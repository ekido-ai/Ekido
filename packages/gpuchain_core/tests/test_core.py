"""Run from packages/gpuchain_core with: python -m unittest discover -s tests"""

import hashlib
import unittest

from gpuchain_core.canonical import canonical_bytes, document_hash
from gpuchain_core.logical import (
    InvalidExecConfig,
    check_exec_config,
    derive_seed,
    feasible_micro_batches,
    learning_rate,
    logical_batch_indices,
    micro_batch_seed,
    micro_loss_weight,
    split_micro_batches,
    step_position,
)


class CanonicalJson(unittest.TestCase):
    def test_keys_sorted_without_whitespace(self):
        self.assertEqual(canonical_bytes({"b": 1, "a": [True, None]}), b'{"a":[true,null],"b":1}')

    def test_rfc8785_key_order_is_utf16(self):
        # U+1F600 encodes as surrogates (0xD83D...), so it sorts before U+FB33 in UTF-16,
        # though Python's default code-point sort puts it after.
        doc = {"\ufb33": 1, "\U0001f600": 2}
        self.assertEqual(canonical_bytes(doc).decode(), '{"\U0001f600":2,"\ufb33":1}')

    def test_numbers_match_ecmascript(self):
        cases = {
            0.0: "0", -0.0: "0", 1.0: "1", 100.0: "100", 0.5: "0.5", -1.5: "-1.5",
            1e21: "1e+21", 1e20: "100000000000000000000", 1e-6: "0.000001", 1e-7: "1e-7",
            1.5e-7: "1.5e-7", 1.5e300: "1.5e+300", 123456789012.5: "123456789012.5",
            1e16: "10000000000000000", 1.2e-5: "0.000012",
        }
        for value, expected in cases.items():
            self.assertEqual(canonical_bytes(value).decode(), expected, msg=repr(value))

    def test_rejects_values_json_cannot_carry(self):
        for bad in (float("nan"), float("inf"), 2**53, {1: "x"}, b"bytes"):
            with self.assertRaises((ValueError, TypeError)):
                canonical_bytes(bad)

    def test_strings_escape_minimally(self):
        self.assertEqual(canonical_bytes('a"\n\u00e9').decode(), '"a\\"\\n\u00e9"')

    def test_hash_ignores_signature_and_key_order(self):
        a = {"x": 1, "y": 2, "signature": "0xaa"}
        b = {"y": 2, "x": 1, "signature": "0xbb"}
        self.assertEqual(document_hash(a), document_hash(b))
        self.assertEqual(document_hash(a), hashlib.sha256(b'{"x":1,"y":2}').hexdigest())

    def test_hash_changes_when_content_changes(self):
        self.assertNotEqual(document_hash({"x": 1}), document_hash({"x": 2}))


class ExecConfig(unittest.TestCase):
    def test_product_must_equal_logical_batch(self):
        check_exec_config({"micro_batch": 8, "accumulation": 4}, 32)
        with self.assertRaises(InvalidExecConfig):
            check_exec_config({"micro_batch": 8, "accumulation": 3}, 32)

    def test_feasible_micro_batches_largest_first(self):
        self.assertEqual(feasible_micro_batches(32), [32, 16, 8, 4, 2, 1])
        self.assertEqual(feasible_micro_batches(12), [12, 6, 4, 3, 2, 1])


class LogicalSteps(unittest.TestCase):
    def test_same_examples_for_any_micro_batch(self):
        indices = logical_batch_indices(1337, 42, 32, 1000)
        self.assertEqual(len(indices), 32)
        for micro in feasible_micro_batches(32):
            parts = split_micro_batches(indices, micro)
            self.assertEqual([i for part in parts for i in part], indices)
            self.assertTrue(all(len(part) == micro for part in parts))

    def test_resume_needs_no_prior_state(self):
        first = logical_batch_indices(1337, 7, 32, 1000)
        for _ in range(3):
            logical_batch_indices(1337, 3, 32, 1000)
        self.assertEqual(logical_batch_indices(1337, 7, 32, 1000), first)

    def test_known_values_stay_stable(self):
        # Pinned: a change here would silently break resuming across code versions.
        self.assertEqual(derive_seed("micro", 1337, 0, 0), micro_batch_seed(1337, 0, 0))
        self.assertEqual(micro_batch_seed(1337, 0, 0),
                         int.from_bytes(hashlib.sha256("micro\x1f1337\x1f0\x1f0".encode()).digest()[:8], "big"))

    def test_epoch_covers_every_example_once(self):
        seen = []
        for step in range(10):
            seen += logical_batch_indices(5, step, 10, 100)
        self.assertEqual(sorted(seen), list(range(100)))

    def test_new_epoch_uses_new_order(self):
        self.assertEqual(step_position(10, 10, 100).epoch, 1)
        self.assertEqual(step_position(10, 10, 100).start, 0)
        self.assertNotEqual(logical_batch_indices(5, 0, 10, 100), logical_batch_indices(5, 10, 10, 100))

    def test_incomplete_final_batch_dropped(self):
        self.assertEqual(step_position(3, 32, 100).epoch, 1)

    def test_batch_larger_than_dataset_rejected(self):
        with self.assertRaises(ValueError):
            step_position(0, 32, 10)

    def test_seeds_differ_per_micro_batch_and_step(self):
        seeds = {micro_batch_seed(1, s, m) for s in range(5) for m in range(5)}
        self.assertEqual(len(seeds), 25)

    def test_loss_weights_sum_to_one(self):
        for sizes in ([32], [16, 16], [8] * 4, [20, 12], [1] * 32):
            self.assertAlmostEqual(sum(micro_loss_weight(s, 32) for s in sizes), 1.0)


class LearningRate(unittest.TestCase):
    schedule = {"name": "linear_warmup_linear_decay", "warmup_steps": 10}

    def test_constant(self):
        self.assertEqual(learning_rate({"name": "constant", "warmup_steps": 0}, 0.1, 50, 100), 0.1)

    def test_warmup_reaches_base(self):
        self.assertAlmostEqual(learning_rate(self.schedule, 1.0, 0, 110), 0.1)
        self.assertAlmostEqual(learning_rate(self.schedule, 1.0, 9, 110), 1.0)

    def test_decay_starts_at_base_and_reaches_zero(self):
        self.assertAlmostEqual(learning_rate(self.schedule, 1.0, 10, 110), 1.0)
        self.assertAlmostEqual(learning_rate(self.schedule, 1.0, 110, 110), 0.0)

    def test_no_warmup_does_not_divide_by_zero(self):
        self.assertAlmostEqual(learning_rate({"name": "linear_warmup_linear_decay", "warmup_steps": 0}, 1.0, 0, 10), 1.0)

    def test_unknown_schedule_rejected(self):
        with self.assertRaises(ValueError):
            learning_rate({"name": "cosine", "warmup_steps": 0}, 1.0, 0, 10)


if __name__ == "__main__":
    unittest.main()
