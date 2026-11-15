import unittest

from ekido_core.canonical import document_hash
from ekido_core.compiler import (
    Decision,
    ProbeResult,
    Target,
    UnsupportedWorkload,
    build_adaptation_manifest,
    candidate_configs,
    check_gates,
    check_workload_layers,
    choose_amp,
    compile_for_target,
    verify_config,
    workload_key,
)

JOB = "00000000-0000-0000-0000-000000000001"


def target(capacity=3072.0, cap="8.6", online=True, free=3000.0, pid="b", torch_version=None):
    return Target(pid, online, capacity, free, cap, torch_version)


def memory_probe(per_example_mib=100.0, base=300.0, speed=10.0, oom_over=True):
    """Fakes a GPU: memory grows with micro-batch size and OOMs over capacity."""
    calls = []

    def probe(t, config):
        calls.append(config)
        needed = base + per_example_mib * config["micro_batch"]
        if config["grad_checkpointing"]:
            needed = base + (per_example_mib / 3) * config["micro_batch"]
        if oom_over and needed > t.capacity_mib:
            return ProbeResult(ok=False, oom=True)
        return ProbeResult(ok=True, peak_mem_mib=needed, steps_per_s=speed, duration_s=1.5)

    probe.calls = calls
    return probe


def compile_(t, probe, batch=32, steps=100, seconds=600, **kw):
    return compile_for_target(t, batch, probe, remaining_steps=steps, seconds_to_deadline=seconds, **kw)


class Gates(unittest.TestCase):
    def test_passes_a_supported_gpu(self):
        self.assertIsNone(check_gates(target()))
        self.assertIsNone(check_gates(target(cap="7.5")))

    def test_rejections_name_their_reason(self):
        cases = [
            (target(online=False), "OFFLINE"),
            (target(cap="6.0"), "GATE_COMPUTE_CAP"),  # Kaggle's P100.
            (target(cap="7.0"), "GATE_COMPUTE_CAP"),
            (target(cap=None), "GATE_COMPUTE_CAP"),
            (target(capacity=None), "GATE_FREE_MEMORY"),
            (target(free=100.0), "GATE_FREE_MEMORY"),
        ]
        for t, code in cases:
            self.assertEqual(check_gates(t)[0], code, msg=str(t))

    def test_torch_mismatch_refused_but_build_suffix_ignored(self):
        self.assertEqual(check_gates(target(torch_version="2.14.0"), "2.15.0")[0], "GATE_TORCH_VERSION")
        self.assertIsNone(check_gates(target(torch_version="2.15.0+cu132"), "2.15.0"))


class CpuFallback(unittest.TestCase):
    def test_cpu_refused_for_real_workloads(self):
        decision = compile_(target(cap="cpu"), memory_probe())
        self.assertFalse(decision.approved)
        self.assertEqual(decision.code, "GATE_COMPUTE_CAP")
        self.assertIn("synthetic", decision.reason)

    def test_cpu_allowed_for_synthetic_and_never_uses_autocast(self):
        decision = compile_(target(cap="cpu", capacity=6144.0), memory_probe(), allow_cpu=True)
        self.assertTrue(decision.approved)
        self.assertEqual(decision.exec_config["amp"], "none")

    def test_cpu_with_no_memory_limit_is_refused_not_a_crash(self):
        decision = compile_(target(cap="cpu", capacity=None), memory_probe(), allow_cpu=True)
        self.assertFalse(decision.approved)
        self.assertEqual(decision.code, "GATE_FREE_MEMORY")


class ProbeBudget(unittest.TestCase):
    def test_budget_spent_keeps_a_proven_config(self):
        # Largest runs out of memory, smallest fits, then the budget runs out during the search.
        decision = compile_(target(), memory_probe(), max_probes=2)
        self.assertTrue(decision.approved)
        self.assertEqual(decision.exec_config["micro_batch"], 1)

    def test_budget_spent_with_nothing_proven_still_rejects(self):
        self.assertFalse(compile_(target(), memory_probe(), max_probes=1).approved)


class Candidates(unittest.TestCase):
    def test_bf16_only_where_native(self):
        self.assertEqual(choose_amp("8.6")[0], "bf16")
        self.assertEqual(choose_amp("7.5"), ["fp16"])  # T4 reports BF16 support through emulation.
        self.assertEqual(choose_amp(None), ["fp16"])

    def test_every_candidate_preserves_the_logical_batch(self):
        for config in candidate_configs(32, "8.6"):
            self.assertEqual(config["micro_batch"] * config["accumulation"], 32)

    def test_fastest_first(self):
        first = candidate_configs(32, "8.6")[0]
        self.assertEqual((first["micro_batch"], first["amp"], first["grad_checkpointing"]), (32, "bf16", False))

    def test_checkpointing_is_a_last_resort(self):
        flags = [c["grad_checkpointing"] for c in candidate_configs(32, "8.6")]
        self.assertEqual(flags, sorted(flags))


class Compile(unittest.TestCase):
    def test_keeps_full_batch_when_it_fits(self):
        decision = compile_(target(capacity=6144.0), memory_probe())
        self.assertTrue(decision.approved)
        self.assertEqual((decision.exec_config["micro_batch"], decision.exec_config["accumulation"]), (32, 1))

    def test_adapts_to_a_memory_cap_keeping_logical_batch(self):
        decision = compile_(target(capacity=2048.0), memory_probe())
        self.assertTrue(decision.approved)
        config = decision.exec_config
        self.assertEqual(config["micro_batch"] * config["accumulation"], 32)
        self.assertLess(config["micro_batch"], 32)
        self.assertLessEqual(decision.probe.peak_mem_mib, 0.85 * 2048)

    def test_every_approval_has_a_real_measurement(self):
        decision = compile_(target(capacity=2048.0), memory_probe())
        self.assertIsNotNone(decision.probe)
        self.assertGreater(decision.probe.steps_per_s, 0)

    def test_t4_style_gpu_gets_fp16(self):
        decision = compile_(target(capacity=15360.0, cap="7.5"), memory_probe())
        self.assertEqual(decision.exec_config["amp"], "fp16")

    def test_refuses_when_nothing_fits(self):
        decision = compile_(target(capacity=200.0, free=None), memory_probe())
        self.assertFalse(decision.approved)
        self.assertEqual(decision.code, "PROBE_OOM")
        self.assertIn("200 MiB", decision.reason)
        self.assertTrue(decision.tried)

    def test_near_capacity_fit_is_refused_by_the_margin(self):
        # Fits technically, but with no room to spare: it would risk a mid-job OOM.
        def probe(t, config):
            return ProbeResult(ok=True, peak_mem_mib=t.capacity_mib * 0.99, steps_per_s=10.0)

        decision = compile_(target(capacity=2048.0), probe)
        self.assertFalse(decision.approved)
        self.assertEqual(decision.code, "OVER_MEMORY_MARGIN")

    def test_too_slow_for_the_deadline(self):
        decision = compile_(target(capacity=6144.0), memory_probe(speed=0.01), steps=100, seconds=60)
        self.assertFalse(decision.approved)
        self.assertEqual(decision.code, "DEADLINE")

    def test_deadline_failure_stops_early(self):
        probe = memory_probe(speed=0.01)
        compile_(target(capacity=6144.0), probe, steps=100, seconds=60)
        self.assertEqual(len(probe.calls), 1)

    def test_gate_failure_never_runs_a_probe(self):
        probe = memory_probe()
        decision = compile_(target(cap="6.0"), probe)
        self.assertEqual(decision.code, "GATE_COMPUTE_CAP")
        self.assertEqual(probe.calls, [])

    def test_unknown_probe_error_is_not_read_as_out_of_memory(self):
        def probe(t, config):
            return ProbeResult(ok=False, error="CUDA driver crashed")

        decision = compile_(target(), probe)
        self.assertEqual((decision.code, decision.reason), ("PROBE_ERROR", "CUDA driver crashed"))
        self.assertEqual(len(decision.tried), 1)

    def test_a_probe_with_no_numbers_cannot_approve(self):
        def probe(t, config):
            return ProbeResult(ok=True, peak_mem_mib=None, steps_per_s=None)

        self.assertFalse(compile_(target(), probe).approved)

    def test_probe_count_is_bounded(self):
        probe = memory_probe(per_example_mib=10_000.0)
        decision = compile_(target(), probe, max_probes=2)
        self.assertEqual(len(probe.calls), 2)
        self.assertIn("stopped after 2", decision.reason)

    def test_full_capacity_needs_one_probe(self):
        probe = memory_probe()
        compile_(target(capacity=6144.0), probe)
        self.assertEqual(len(probe.calls), 1)

    def test_hopeless_provider_is_refused_in_three_probes(self):
        probe = memory_probe()
        self.assertFalse(compile_(target(capacity=200.0, free=None), probe).approved)
        self.assertEqual(len(probe.calls), 3)

    def test_search_finds_the_largest_fit_without_trying_everything(self):
        probe = memory_probe()
        decision = compile_(target(capacity=2048.0), probe)
        self.assertEqual(decision.exec_config["micro_batch"], 8)  # 16 needs 1900 MiB, over 85% of 2048.
        self.assertLess(len(probe.calls), 6)

    def test_grad_checkpointing_rescues_a_tight_fit(self):
        # Plain micro-batch 1 needs 500 MiB. With checkpointing it needs 367, under 85% of 450.
        decision = compile_(target(capacity=450.0, free=None), memory_probe(base=300.0, per_example_mib=200.0))
        self.assertTrue(decision.approved)
        self.assertTrue(decision.exec_config["grad_checkpointing"])
        self.assertEqual(decision.exec_config["micro_batch"], 1)

    def test_every_size_of_cap_gets_the_true_largest_fit(self):
        # Compared with trying every option, for many caps.
        for capacity in range(450, 6200, 137):
            needed = {m: 300 + 100 * m for m in (32, 16, 8, 4, 2, 1)}
            fits = [m for m, need in needed.items() if need <= 0.85 * capacity]
            decision = compile_(target(capacity=float(capacity), free=None), memory_probe())
            if fits:
                self.assertEqual(decision.exec_config["micro_batch"], max(fits), msg=f"cap {capacity}")


class VerifyQualified(unittest.TestCase):
    config = {"micro_batch": 8, "accumulation": 4, "amp": "bf16", "grad_checkpointing": False, "attention_impl": "sdpa", "loader_workers": 0}

    def verify(self, t, probe, **kw):
        return verify_config(t, self.config, probe, remaining_steps=kw.get("steps", 100), seconds_to_deadline=kw.get("seconds", 600))

    def test_uses_exactly_one_fresh_probe(self):
        probe = memory_probe()
        decision = self.verify(target(capacity=2048.0), probe)
        self.assertTrue(decision.approved)
        self.assertEqual(probe.calls, [self.config])
        self.assertIsNotNone(decision.probe)

    def test_a_changed_situation_is_caught(self):
        self.assertEqual(self.verify(target(capacity=500.0, free=None), memory_probe()).code, "PROBE_OOM")
        self.assertEqual(self.verify(target(online=False), memory_probe()).code, "OFFLINE")

    def test_deadline_is_checked_again(self):
        self.assertEqual(self.verify(target(capacity=2048.0), memory_probe(speed=0.01), seconds=60).code, "DEADLINE")


class WorkloadKey(unittest.TestCase):
    spec = {"template": "t", "logical_batch_size": 32, "max_seq_length": 128, "lora": {"r": 8}, "model": {"id": "m"}, "seed": 1, "total_logical_steps": 100}

    def test_ignores_what_does_not_affect_memory(self):
        self.assertEqual(workload_key(self.spec), workload_key(dict(self.spec, seed=2, total_logical_steps=999)))

    def test_changes_with_what_does(self):
        for change in ({"logical_batch_size": 64}, {"max_seq_length": 256}, {"lora": {"r": 16}}, {"model": {"id": "other"}}):
            self.assertNotEqual(workload_key(self.spec), workload_key(dict(self.spec, **change)), msg=str(change))


class Workloads(unittest.TestCase):
    def test_batchnorm_refused(self):
        with self.assertRaises(UnsupportedWorkload):
            check_workload_layers(["Linear", "BatchNorm2d"])

    def test_layernorm_allowed(self):
        check_workload_layers(["Linear", "LayerNorm", "Dropout"])


class Manifest(unittest.TestCase):
    source_exec = {"micro_batch": 32, "accumulation": 1, "amp": "bf16", "grad_checkpointing": False, "attention_impl": "sdpa", "loader_workers": 0}

    def build(self, decision, rejected=()):
        return build_adaptation_manifest(
            job_id=JOB, attempt=2, from_checkpoint="a" * 64, from_provider="a", from_exec=self.source_exec,
            immutable_hash="b" * 64, logical_batch_size=32, approved=decision, rejected=list(rejected), created_at="2026-11-04T00:00:00+00:00",
        )

    def test_records_every_change_with_a_reason(self):
        manifest, _ = self.build(compile_(target(capacity=2048.0), memory_probe()))
        fields = {c["field"] for c in manifest["changes"]}
        self.assertEqual(fields, {"micro_batch", "accumulation"})
        self.assertTrue(all(c["reason"] for c in manifest["changes"]))

    def test_no_changes_when_config_is_kept(self):
        manifest, _ = self.build(compile_(target(capacity=6144.0), memory_probe()))
        self.assertEqual(manifest["changes"], [])

    def test_records_precision_change(self):
        manifest, _ = self.build(compile_(target(capacity=15360.0, cap="7.5"), memory_probe()))
        amp = next(c for c in manifest["changes"] if c["field"] == "amp")
        self.assertEqual((amp["from"], amp["to"]), ("bf16", "fp16"))

    def test_records_rejected_candidates(self):
        refused = compile_(target(capacity=200.0, free=None, pid="c"), memory_probe())
        manifest, _ = self.build(compile_(target(capacity=2048.0), memory_probe()), [refused])
        self.assertEqual(manifest["rejected_candidates"][0]["provider_id"], "c")
        self.assertEqual(manifest["rejected_candidates"][0]["code"], "PROBE_OOM")

    def test_hash_matches_canonical_form(self):
        manifest, digest = self.build(compile_(target(capacity=2048.0), memory_probe()))
        self.assertEqual(digest, document_hash(manifest))

    def test_cannot_build_without_a_real_probe(self):
        with self.assertRaises(ValueError):
            self.build(Decision("x", approved=True, exec_config=self.source_exec, probe=None))


if __name__ == "__main__":
    unittest.main()
