"""Elastic GPU Compiler: decides how a job can run on a replacement GPU, or refuses.

Only execution settings can change; the job spec is immutable. A config is approved only by a real
probe on the target. Estimates can order candidates but can never approve one. Standard library
only: the probe is passed in, since it runs on the provider. Rejecting is a normal, useful outcome.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Iterable

from .canonical import document_hash
from .logical import check_exec_config, feasible_micro_batches

MIN_COMPUTE_CAP = (7, 5)  # Turing. The current CUDA 13 wheels don't support older GPUs.
CPU_DEVICE = "cpu"  # Reported in place of a compute capability. Only for the synthetic fallback workload.
DEFAULT_MEMORY_MARGIN = 0.85
DEFAULT_MIN_FREE_MIB = 300.0
UNSUPPORTED_LAYERS = frozenset({"BatchNorm1d", "BatchNorm2d", "BatchNorm3d", "SyncBatchNorm"})


class UnsupportedWorkload(ValueError):
    pass


def check_workload_layers(layer_types: Iterable[str]) -> None:
    """BatchNorm statistics change with micro-batch size, so a resume wouldn't preserve training behaviour."""
    found = UNSUPPORTED_LAYERS.intersection(layer_types)
    if found:
        raise UnsupportedWorkload(f"micro-batch adaptation isn't safe with: {sorted(found)}")


@dataclass(frozen=True)
class Target:
    provider_id: str
    online: bool
    capacity_mib: float | None  # The enforced limit: real VRAM, or the cap for a capped profile.
    free_mib: float | None
    compute_cap: str | None
    torch_version: str | None = None


@dataclass(frozen=True)
class ProbeResult:
    ok: bool
    peak_mem_mib: float | None = None
    steps_per_s: float | None = None
    duration_s: float | None = None
    oom: bool = False
    error: str | None = None


ProbeFn = Callable[[Target, dict], ProbeResult]


@dataclass
class Decision:
    provider_id: str
    approved: bool
    exec_config: dict | None = None
    probe: ProbeResult | None = None
    capacity_mib: float | None = None
    code: str | None = None
    reason: str | None = None
    tried: list[dict] = field(default_factory=list)
    needs_fresh_probe: bool = False  # Approved on an earlier measurement. Must be re-measured before it's used.


def _parse_cap(cap: str | None) -> tuple[int, int] | None:
    try:
        major, minor = (cap or "").split(".")
        return int(major), int(minor)
    except ValueError:
        return None


def check_gates(target: Target, required_torch: str | None = None, min_free_mib: float = DEFAULT_MIN_FREE_MIB, *, allow_cpu: bool = False) -> tuple[str, str] | None:
    """Hard gates, cheap to check, before spending time on a probe. Returns (code, reason) or None."""
    if not target.online:
        return "OFFLINE", "Provider is offline"
    if target.compute_cap == CPU_DEVICE:
        if not allow_cpu:
            return "GATE_COMPUTE_CAP", "CPU providers can only run the synthetic fallback workload"
        # A CPU reports no GPU memory, so it needs a declared limit for the margin check.
        return None if target.capacity_mib else ("GATE_FREE_MEMORY", "This CPU provider has no memory limit set")
    cap = _parse_cap(target.compute_cap)
    if cap is None:
        return "GATE_COMPUTE_CAP", "GPU compute capability is unknown, so compatibility can't be established"
    if cap < MIN_COMPUTE_CAP:
        return "GATE_COMPUTE_CAP", f"Compute capability {target.compute_cap} is below the {MIN_COMPUTE_CAP[0]}.{MIN_COMPUTE_CAP[1]} the runtime's CUDA build needs"
    if required_torch and target.torch_version and target.torch_version.split("+")[0] != required_torch.split("+")[0]:
        return "GATE_TORCH_VERSION", f"Provider runs torch {target.torch_version}, job needs {required_torch}"
    if target.capacity_mib is None or target.capacity_mib <= 0:
        return "GATE_FREE_MEMORY", "GPU memory capacity is unknown"
    if target.free_mib is not None and target.free_mib < min_free_mib:
        return "GATE_FREE_MEMORY", f"Only {target.free_mib:.0f} MiB free, needs at least {min_free_mib:.0f} MiB"
    return None


def choose_amp(compute_cap: str | None) -> list[str]:
    """One mode per GPU. Native BF16 needs no loss scaler. Measured peak memory matches FP16's, so trying both only slows recovery."""
    if compute_cap == CPU_DEVICE:
        return ["none"]
    cap = _parse_cap(compute_cap)
    if cap is not None and cap >= (8, 0):
        return ["bf16"]
    return ["fp16"]


def candidate_configs(logical_batch_size: int, compute_cap: str | None, *, base: dict | None = None) -> list[dict]:
    """Fastest first: largest micro-batch with no gradient checkpointing, ending with the smallest footprint."""
    base = base or {}
    configs = []
    amps = choose_amp(compute_cap)
    for grad_checkpointing in (False, True):
        for micro in feasible_micro_batches(logical_batch_size):
            for amp in amps:
                config = {
                    "micro_batch": micro,
                    "accumulation": logical_batch_size // micro,
                    "amp": amp,
                    "grad_checkpointing": grad_checkpointing,
                    "attention_impl": base.get("attention_impl", "sdpa"),
                    "loader_workers": base.get("loader_workers", 0),
                }
                check_exec_config(config, logical_batch_size)
                configs.append(config)
    # Keep the search short in a live recovery: a smaller micro-batch is tried before checkpointing is.
    configs.sort(key=lambda c: (c["grad_checkpointing"], -c["micro_batch"], amps.index(c["amp"])))
    return configs


def compile_for_target(
    target: Target,
    logical_batch_size: int,
    probe: ProbeFn,
    *,
    remaining_steps: int,
    seconds_to_deadline: float,
    required_torch: str | None = None,
    memory_margin: float = DEFAULT_MEMORY_MARGIN,
    max_probes: int = 8,
    allow_cpu: bool = False,
) -> Decision:
    """Finds the largest micro-batch a real probe proves fits with margin, or refuses.

    Probes are slow (about 8 s each measured on the demo laptop), so this searches instead of
    trying everything: largest first, then smallest, then a binary search between them. Memory
    use grows with micro-batch size, so the search only needs that ordering.
    """
    decision = Decision(target.provider_id, approved=False, capacity_mib=target.capacity_mib)
    gate = check_gates(target, required_torch, allow_cpu=allow_cpu)
    if gate:
        decision.code, decision.reason = gate
        return decision

    amp = choose_amp(target.compute_cap)[0]
    micros = feasible_micro_batches(logical_batch_size)
    limit = memory_margin * target.capacity_mib
    state = {"code": "PROBE_OOM", "reason": "No config fits", "probes": 0}

    class ProbeFailed(Exception):
        pass

    class BudgetSpent(Exception):
        pass

    def attempt(micro: int, grad_checkpointing: bool = False) -> tuple[dict, ProbeResult] | None:
        """The config and its result if it fits with margin, or None. Anything unexplained stops the search."""
        if state["probes"] >= max_probes:
            state["reason"] += f" (stopped after {max_probes} probes)"
            raise BudgetSpent
        state["probes"] += 1
        config = {
            "micro_batch": micro,
            "accumulation": logical_batch_size // micro,
            "amp": amp,
            "grad_checkpointing": grad_checkpointing,
            "attention_impl": "sdpa",
            "loader_workers": 0,
        }
        result = probe(target, config)
        decision.tried.append(config)
        if result.oom:
            state["code"], state["reason"] = "PROBE_OOM", f"Out of memory at micro-batch {micro} ({amp}) under {target.capacity_mib:.0f} MiB"
            return None
        if not result.ok or result.peak_mem_mib is None or not result.steps_per_s:
            # An unknown failure isn't evidence that a smaller config would work.
            decision.code, decision.reason = "PROBE_ERROR", result.error or "Probe returned no usable measurement"
            raise ProbeFailed
        if result.peak_mem_mib > limit:
            state["code"] = "OVER_MEMORY_MARGIN"
            state["reason"] = f"Peak {result.peak_mem_mib:.0f} MiB at micro-batch {micro} is over the {limit:.0f} MiB safety limit"
            return None
        return config, result

    best = None
    try:
        best = attempt(micros[0])
        if best is None and len(micros) > 1:
            smallest = attempt(micros[-1])
            if smallest is None:
                # Last resort: trade speed for memory at the smallest micro-batch.
                best = attempt(micros[-1], grad_checkpointing=True)
            else:
                best = smallest
                low, high = 0, len(micros) - 1  # micros[low] doesn't fit, micros[high] does.
                while high - low > 1:
                    middle = (low + high) // 2
                    found = attempt(micros[middle])
                    if found is None:
                        low = middle
                    else:
                        best, high = found, middle
    except ProbeFailed:
        return decision
    except BudgetSpent:
        # Running out of probes is no evidence against a config a probe already proved fits. Found by Vaibhav.
        pass

    if best is None:
        decision.code, decision.reason = state["code"], state["reason"]
        return decision
    return _accept(decision, best[0], best[1], remaining_steps, seconds_to_deadline)


def _accept(decision: Decision, config: dict, result: ProbeResult, remaining_steps: int, seconds_to_deadline: float) -> Decision:
    eta = remaining_steps / result.steps_per_s
    if eta > seconds_to_deadline:
        decision.code = "DEADLINE"
        decision.reason = f"Measured {result.steps_per_s:.2f} steps/s needs {eta:.0f}s, but only {seconds_to_deadline:.0f}s remain"
        return decision
    decision.approved = True
    decision.exec_config = config
    decision.probe = result
    return decision


def verify_config(target: Target, config: dict, probe: ProbeFn, *, remaining_steps: int, seconds_to_deadline: float, memory_margin: float = DEFAULT_MEMORY_MARGIN, allow_cpu: bool = False) -> Decision:
    """One fresh probe of a config qualified earlier, so a fast recovery still rests on a real measurement now."""
    decision = Decision(target.provider_id, approved=False, capacity_mib=target.capacity_mib)
    gate = check_gates(target, allow_cpu=allow_cpu)
    if gate:
        decision.code, decision.reason = gate
        return decision
    result = probe(target, config)
    decision.tried.append(config)
    if result.oom:
        decision.code, decision.reason = "PROBE_OOM", f"Out of memory at micro-batch {config['micro_batch']} under {target.capacity_mib:.0f} MiB"
        return decision
    if not result.ok or result.peak_mem_mib is None or not result.steps_per_s:
        decision.code, decision.reason = "PROBE_ERROR", result.error or "Probe returned no usable measurement"
        return decision
    if result.peak_mem_mib > memory_margin * target.capacity_mib:
        decision.code, decision.reason = "OVER_MEMORY_MARGIN", f"Peak {result.peak_mem_mib:.0f} MiB is over the safety limit"
        return decision
    return _accept(decision, config, result, remaining_steps, seconds_to_deadline)


def workload_key(spec: dict) -> str:
    """What decides a config's memory use. Two jobs matching on this can share qualification results."""
    fields = ("template", "logical_batch_size", "max_seq_length", "lora", "model", "dropout")
    return document_hash({name: spec.get(name) for name in fields})


def describe_changes(old: dict, new: dict, decision: Decision) -> list[dict]:
    reasons = {
        "micro_batch": f"Largest micro-batch that fits {decision.capacity_mib:.0f} MiB, measured by probe",
        "accumulation": "Keeps the logical batch size constant",
        "amp": "BF16 isn't native on this GPU" if new.get("amp") == "fp16" else "Native BF16 is available",
        "grad_checkpointing": "Needed to reduce peak memory" if new.get("grad_checkpointing") else "Not needed on this GPU",
        "attention_impl": "Selected for this GPU",
        "loader_workers": "Selected for this host",
    }
    return [
        {"field": name, "from": old[name], "to": new[name], "reason": reasons[name]}
        for name in ("micro_batch", "accumulation", "amp", "grad_checkpointing", "attention_impl", "loader_workers")
        if old.get(name) != new.get(name)
    ]


def build_adaptation_manifest(
    *,
    job_id: str,
    attempt: int,
    from_checkpoint: str,
    from_provider: str,
    from_exec: dict,
    immutable_hash: str,
    logical_batch_size: int,
    approved: Decision,
    rejected: list[Decision],
    created_at: str | None = None,
) -> tuple[dict, str]:
    """The record of what changed and why. Its hash is anchored on-chain and in the next checkpoint."""
    if not approved.approved or approved.exec_config is None or approved.probe is None:
        raise ValueError("a manifest needs an approved decision with a real probe")
    manifest = {
        "schema_version": 1,
        "job_id": job_id,
        "attempt": attempt,
        "from_checkpoint": from_checkpoint,
        "from": {"provider_id": from_provider, "exec": from_exec},
        "to": {"provider_id": approved.provider_id, "exec": approved.exec_config},
        "invariants": {"immutable_hash": immutable_hash, "logical_batch_size": logical_batch_size},
        "changes": describe_changes(from_exec, approved.exec_config, approved),
        "rejected_candidates": [
            {"provider_id": d.provider_id, "code": d.code, "reason": d.reason, "tried": d.tried} for d in rejected
        ],
        "probe": {
            "peak_mem_mib": approved.probe.peak_mem_mib,
            "capacity_mib": approved.capacity_mib,
            "steps_per_s": approved.probe.steps_per_s,
            "duration_s": approved.probe.duration_s or 0,
        },
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
    }
    return manifest, document_hash(manifest)
