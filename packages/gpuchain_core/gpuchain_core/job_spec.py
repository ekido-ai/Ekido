"""What a job must say before the coordinator accepts it.

A spec's hash goes on-chain and a client pays against it, so an incomplete one must be refused at the
door instead of failing later on a provider. Full schemas: docs/schemas/job_spec.schema.json and
quality_policy.schema.json. This checks what the workers really read, and is dependency-free.
"""

from __future__ import annotations

from .data_identity import validate_spec_identity

TEMPLATES = ("distilbert-lora-agnews/v1", "synthetic-linear/v1", "custom-python/v1")
MAX_PROBATION_MARGIN = 0.15  # Wider than this, a mid-training check would stop catching real damage.
POLICY_FIELDS = ("min_absolute", "non_inferiority_margin", "confidence", "bootstrap_resamples", "eval_set_hash", "eval_version_hash")


def _whole(spec: dict, name: str, minimum: int, problems: list[str]) -> None:
    value = spec.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        problems.append(f"{name} must be a whole number of at least {minimum}")


def _section(spec: dict, name: str, fields: tuple[str, ...], problems: list[str]) -> None:
    section = spec.get(name)
    if not isinstance(section, dict):
        problems.append(f"{name} is missing")
        return
    problems.extend(f"{name}.{field} is missing" for field in fields if field not in section)


def spec_problems(spec: dict) -> list[str]:
    """Everything wrong with a workload, in words a client can act on. Empty means it's acceptable."""
    template = spec.get("template")
    if template not in TEMPLATES:
        return [f"template must be one of {', '.join(TEMPLATES)}"]
    problems: list[str] = []
    _whole(spec, "logical_batch_size", 1, problems)
    _whole(spec, "total_logical_steps", 1, problems)
    _whole(spec, "seed", 0, problems)
    if "checkpoint_every_steps" in spec:
        _whole(spec, "checkpoint_every_steps", 1, problems)
    if "train_examples" in spec:
        _whole(spec, "train_examples", 1, problems)
    _section(spec, "optimizer", ("name", "lr", "weight_decay", "betas", "eps", "max_grad_norm"), problems)
    _section(spec, "lr_schedule", ("name", "warmup_steps"), problems)
    if template == "distilbert-lora-agnews/v1":
        _section(spec, "model", ("id", "revision"), problems)
        _section(spec, "dataset", ("id", "split", "fingerprint"), problems)
        _section(spec, "lora", ("r", "alpha", "dropout", "target_modules"), problems)
        _whole(spec, "max_seq_length", 8, problems)
        try:
            validate_spec_identity(spec)
        except (KeyError, TypeError, ValueError) as exc:
            problems.append(f"invalid data identity: {exc}")
    from .protocol_fee import fee_problems

    problems.extend(fee_problems(spec))
    if template == "custom-python/v1":
        code = spec.get("code")
        if not isinstance(code, dict) or not _is_sha256(code.get("sha256")):
            problems.append("code.sha256 must be the SHA-256 of job.py")
        files = spec.get("files", {})
        if not isinstance(files, dict) or not all(isinstance(k, str) and _safe_name(k) and _is_sha256(v) for k, v in files.items()):
            problems.append("files must map plain file names to SHA-256 hashes")
        if "user_config" in spec and not isinstance(spec["user_config"], dict):
            problems.append("user_config must be an object")
    return problems


def _is_sha256(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _safe_name(name: str) -> bool:
    """No folders, no hidden files and no tricks: the name is used as a path inside the sandbox."""
    return 0 < len(name) <= 120 and "/" not in name and "\\" not in name and not name.startswith(".") and name not in ("..", ".")


def policy_problems(policy: dict) -> list[str]:
    """Verifiers can't judge a job without these. Only enforced when a quality gate is running."""
    problems = [f"policy.{field} is missing" for field in POLICY_FIELDS if field not in policy]
    probation = policy.get("probation_margin")
    if probation is not None and "non_inferiority_margin" in policy and not policy["non_inferiority_margin"] <= probation <= MAX_PROBATION_MARGIN:
        problems.append(f"policy.probation_margin must be between non_inferiority_margin and {MAX_PROBATION_MARGIN}")
    return problems
