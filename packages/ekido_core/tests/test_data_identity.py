import unittest
import ast
import json
from pathlib import Path
try:
    import jsonschema
except ImportError:
    jsonschema = None

from ekido_core.data_identity import apply_identity, check_split, hash_text_labels, validate_spec_identity


class DataIdentityTests(unittest.TestCase):
    def test_hash_detects_text_label_and_order_changes(self):
        rows = [{"text": "first", "label": 0}, {"text": "second", "label": 1}]
        digest = hash_text_labels(rows)
        check_split(rows, digest, "train")
        for other in (list(reversed(rows)), [{"text": "First", "label": 0}, rows[1]],
                      [rows[0], {"text": "second", "label": 0}]):
            with self.assertRaisesRegex(ValueError, "mismatch"):
                check_split(other, digest, "train")

    def test_identity_pins_a_copy_and_rejects_placeholders(self):
        spec = {"template": "distilbert-lora-agnews/v1", "model": {"id": "model", "revision": "main"},
                "dataset": {"id": "dataset", "fingerprint": "0" * 64}}
        identity = {"model_id": "model", "dataset_id": "dataset", "model_revision": "a" * 40,
                    "dataset_revision": "b" * 40, "train_sha256": "c" * 64, "test_sha256": "d" * 64}
        pinned = apply_identity(spec, identity)
        self.assertEqual(spec["model"]["revision"], "main")
        self.assertEqual(pinned["dataset"]["fingerprint"], "c" * 64)
        for changes in ({"model_revision": "main"}, {"dataset_revision": "main"}, {"model_revision": "0" * 40},
                        {"train_sha256": "0" * 64}, {"dataset_id": "other"}):
            with self.assertRaises(ValueError):
                apply_identity(spec, dict(identity, **changes))

    def test_rejects_partial_and_inconsistent_identity_but_accepts_legacy(self):
        base = {"template": "distilbert-lora-agnews/v1", "model": {"id": "model", "revision": "main"}, "dataset": {"id": "dataset", "fingerprint": "0" * 64}}
        self.assertFalse(validate_spec_identity(base))
        with self.assertRaises(ValueError):
            validate_spec_identity({**base, "dataset": {**base["dataset"], "revision": "a" * 40}})
        identity = {"model_id": "model", "dataset_id": "dataset", "model_revision": "a" * 40, "dataset_revision": "b" * 40, "train_sha256": "c" * 64, "test_sha256": "d" * 64}
        pinned = apply_identity(base, identity)
        self.assertTrue(validate_spec_identity(pinned))
        with self.assertRaises(ValueError):
            validate_spec_identity({**pinned, "dataset": {**pinned["dataset"], "fingerprint": "e" * 64}})
        with self.assertRaises(ValueError):
            apply_identity({**base, "provider_terms": []}, identity)

    @unittest.skipIf(jsonschema is None, "jsonschema not installed")
    @unittest.skipUnless((Path(__file__).resolve().parents[3] / "experiments/quality_comparison.py").exists(),
                         "experiments/quality_comparison.py not in this checkout yet")
    def test_pinned_real_experiment_spec_matches_job_schema(self):
        root = Path(__file__).resolve().parents[3]
        module = ast.parse((root / "experiments/quality_comparison.py").read_text(encoding="utf-8"))
        fn = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "real_spec")
        namespace = {}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), "quality_comparison.py", "exec"), namespace)
        spec = namespace["real_spec"](400, 1)
        identity = {"model_id": spec["model"]["id"], "dataset_id": spec["dataset"]["id"],
                    "model_revision": "a" * 40, "dataset_revision": "b" * 40,
                    "train_sha256": "c" * 64, "test_sha256": "d" * 64}
        schema = json.loads((root / "docs/schemas/job_spec.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        pinned = apply_identity(spec, identity)
        jsonschema.validate(pinned, schema)
        wallet = "0x" + "1" * 40
        quote = {"kind": "gpuchain.provider_quote.v1", "job_id": "12345678-1234-1234-1234-123456789abc",
                 "onchain_job_id": "0x" + "2" * 64, "chain_id": 1, "contract": wallet,
                 "provider_id": "provider", "wallet": wallet, "price_per_step": "1",
                 "workload_hash": "3" * 64, "signature": "0x" + "4" * 130}
        pinned["provider_terms"] = [{"provider_id": "provider", "wallet": wallet, "price_per_step": "1", "quote": quote}]
        jsonschema.validate(pinned, schema)
        del pinned["dataset"]["test_content_sha256"]
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(pinned, schema)


if __name__ == "__main__":
    unittest.main()
