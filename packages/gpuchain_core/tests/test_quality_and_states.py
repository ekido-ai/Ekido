import unittest

from gpuchain_core.job_states import ONCHAIN_STATE, TERMINAL, TRANSITIONS, IllegalTransition, JobState, check_transition
from gpuchain_core.quality import compare_paired, decide, macro_f1, mcnemar_exact_p


def vectors(both: int, cand_only: int, ref_only: int, neither: int):
    candidate = [True] * both + [True] * cand_only + [False] * ref_only + [False] * neither
    reference = [True] * both + [False] * cand_only + [True] * ref_only + [False] * neither
    return candidate, reference


def compare(*counts, seed=1, confidence=0.95, resamples=2000):
    candidate, reference = vectors(*counts)
    return compare_paired(candidate, reference, confidence=confidence, resamples=resamples, seed=seed)


class PairedBootstrap(unittest.TestCase):
    def test_identical_models_have_zero_difference(self):
        result = compare(900, 0, 0, 100)
        self.assertEqual(result.difference, 0)
        self.assertEqual(result.ci_lower, 0)
        self.assertEqual(result.mcnemar_p, 1.0)

    def test_point_estimates(self):
        result = compare(850, 50, 30, 70)
        self.assertAlmostEqual(result.candidate_accuracy, 0.90)
        self.assertAlmostEqual(result.reference_accuracy, 0.88)
        self.assertAlmostEqual(result.difference, 0.02)
        self.assertLess(result.ci_lower, result.difference)

    def test_same_seed_repeats_and_different_seed_can_differ(self):
        self.assertEqual(compare(850, 50, 30, 70, seed=7).ci_lower, compare(850, 50, 30, 70, seed=7).ci_lower)

    def test_lower_bound_matches_normal_approximation(self):
        # d has variance (b + c - (b - c)^2 / n) / n^2. Known answer within sampling tolerance.
        n, b, c = 10000, 500, 300
        result = compare(8700, b, c, n - 8700 - b - c, resamples=20000)
        mean = (b - c) / n
        se = ((b + c - (b - c) ** 2 / n) ** 0.5) / n
        self.assertAlmostEqual(result.ci_lower, mean - 1.645 * se, delta=0.0006)

    def test_mismatched_lengths_are_not_comparable(self):
        with self.assertRaises(ValueError):
            compare_paired([True], [True, False], confidence=0.95, resamples=10, seed=1)

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            compare_paired([], [], confidence=0.95, resamples=10, seed=1)

    def test_all_examples_discordant_does_not_crash(self):
        result = compare(0, 10, 0, 0, resamples=50)
        self.assertEqual(result.difference, 1.0)

    def test_large_set_is_fast_enough_for_a_live_demo(self):
        result = compare(6500, 300, 300, 500)
        self.assertEqual(result.n, 7600)


class McNemar(unittest.TestCase):
    def test_known_values(self):
        self.assertEqual(mcnemar_exact_p(0, 0), 1.0)
        self.assertAlmostEqual(mcnemar_exact_p(1, 9), 0.021484375)  # 2 * (1 + 10) / 2^10
        self.assertEqual(mcnemar_exact_p(5, 5), 1.0)

    def test_large_counts_do_not_overflow(self):
        self.assertLess(mcnemar_exact_p(100, 5000), 1e-10)


class Policy(unittest.TestCase):
    def test_small_noise_passes(self):
        self.assertEqual(decide(compare(6800, 40, 45, 715), margin=0.02, min_absolute=0.88, is_final=False).verdict, "PASS")

    def test_clear_degradation_fails(self):
        decision = decide(compare(5000, 50, 1900, 650), margin=0.02, min_absolute=0.5, is_final=False)
        self.assertEqual(decision.verdict, "FAIL")
        self.assertIn("NON_INFERIORITY_FAILED", decision.reasons)

    def test_small_set_cannot_confirm_a_small_drop_is_safe(self):
        # The same 1-point mean drop passes on a large set and fails on a small one, which is the reason for a large eval set.
        small = compare(780, 8, 17, 95)
        large = compare(6240, 64, 136, 760)
        self.assertEqual(round(small.difference, 2), -0.01)
        self.assertEqual(round(large.difference, 2), -0.01)
        self.assertEqual(decide(large, margin=0.02, min_absolute=0, is_final=False).verdict, "PASS")
        self.assertEqual(decide(small, margin=0.015, min_absolute=0, is_final=False).verdict, "FAIL")

    def test_floor_applies_to_final_only(self):
        result = compare(700, 0, 0, 300)
        self.assertEqual(decide(result, margin=0.02, min_absolute=0.88, is_final=False).verdict, "PASS")
        decision = decide(result, margin=0.02, min_absolute=0.88, is_final=True)
        self.assertEqual(decision.reasons, ["BELOW_ABSOLUTE_FLOOR"])

    def test_good_metric_cannot_rescue_failed_integrity_checks(self):
        result = compare(900, 50, 0, 50)
        for flag, reason in (
            ("signature_valid", "INVALID_SIGNATURE"),
            ("lineage_valid", "INVALID_LINEAGE"),
            ("no_nan_inf", "NAN_OR_INF"),
            ("weights_changed", "WEIGHTS_UNCHANGED"),
        ):
            decision = decide(result, margin=0.02, min_absolute=0, is_final=False, **{flag: False})
            self.assertEqual((decision.verdict, decision.reasons), ("FAIL", [reason]))

    def test_all_failures_are_reported(self):
        decision = decide(compare(100, 0, 500, 400), margin=0.02, min_absolute=0.9, is_final=True, no_nan_inf=False)
        self.assertEqual(set(decision.reasons), {"NAN_OR_INF", "NON_INFERIORITY_FAILED", "BELOW_ABSOLUTE_FLOOR"})


class MacroF1(unittest.TestCase):
    def test_perfect(self):
        self.assertEqual(macro_f1([0, 1, 2], [0, 1, 2]), 1.0)

    def test_known_value(self):
        # Class 0: tp1 fp1 fn0 -> 2/3. Class 1: tp1 fp0 fn1 -> 2/3.
        self.assertAlmostEqual(macro_f1([0, 0, 1], [0, 1, 1]), 2 / 3)

    def test_missed_class_scores_zero(self):
        self.assertAlmostEqual(macro_f1([0, 0], [0, 1]), (2 / 3 + 0) / 2)


class States(unittest.TestCase):
    def test_happy_path(self):
        path = ["OPEN", "ASSIGNED", "RUNNING", "RECOVERING", "RUNNING", "VALIDATING", "COMPLETED", "SETTLED"]
        for a, b in zip(path, path[1:]):
            check_transition(JobState(a), JobState(b))

    def test_rollback_and_failure_paths(self):
        check_transition(JobState.VALIDATING, JobState.RECOVERING)
        check_transition(JobState.RECOVERING, JobState.FAILED)
        check_transition(JobState.FAILED, JobState.REFUNDED)
        check_transition(JobState.COMPLETED, JobState.DISPUTED)

    def test_illegal_moves_rejected(self):
        for a, b in (("OPEN", "SETTLED"), ("RUNNING", "SETTLED"), ("RUNNING", "COMPLETED"), ("FAILED", "RUNNING"), ("SETTLED", "REFUNDED")):
            with self.assertRaises(IllegalTransition):
                check_transition(JobState(a), JobState(b))

    def test_cannot_reach_settled_without_validating(self):
        into_completed = [s for s, targets in TRANSITIONS.items() if JobState.COMPLETED in targets]
        self.assertEqual(into_completed, [JobState.VALIDATING])

    def test_terminal_states(self):
        self.assertEqual(TERMINAL, {JobState.SETTLED, JobState.REFUNDED, JobState.CANCELLED})

    def test_every_state_has_an_onchain_mapping(self):
        self.assertEqual(set(ONCHAIN_STATE), set(JobState))


if __name__ == "__main__":
    unittest.main()
