"""The API contract (docs/api/v1.yaml) stays well-formed while everyone builds against it."""
import re
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # CI installs PyYAML for this suite; skip cleanly elsewhere.
    yaml = None

CONTRACT = Path(__file__).resolve().parents[2] / "docs" / "api" / "v1.yaml"
METHODS = {"get", "post", "put", "patch", "delete"}


@unittest.skipIf(yaml is None, "PyYAML not installed")
class ApiContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = CONTRACT.read_text(encoding="utf-8")
        cls.doc = yaml.safe_load(cls.text)

    def test_is_openapi_3_1(self):
        self.assertEqual(self.doc["openapi"], "3.1.0")

    def test_every_reference_resolves(self):
        for kind, name in re.findall(r"#/components/(\w+)/(\w+)", self.text):
            self.assertIn(name, self.doc["components"].get(kind, {}), f"#/components/{kind}/{name} is referenced but not defined")

    def test_every_operation_has_a_tag_summary_and_responses(self):
        known_tags = {t["name"] for t in self.doc["tags"]}
        for path, item in self.doc["paths"].items():
            for method, op in item.items():
                if method not in METHODS:
                    continue
                where = f"{method.upper()} {path}"
                self.assertTrue(op.get("summary"), f"{where} has no summary")
                self.assertTrue(set(op.get("tags", [])) <= known_tags and op.get("tags"), f"{where} has an unknown or missing tag")
                self.assertTrue(op.get("responses"), f"{where} has no responses")

    def test_customer_schemas_never_expose_providers(self):
        # Hide providers: nothing a customer receives may name a provider, its wallet or its hardware.
        for name in ("CustomerJob", "CustomerEvent", "Model", "Quote", "SavingsReport"):
            fields = set(self.doc["components"]["schemas"][name].get("properties", {}))
            leaked = {f for f in fields if re.search(r"provider|wallet|gpu|device_name", f)}
            self.assertFalse(leaked, f"{name} exposes {leaked}")

    def test_money_is_in_paise(self):
        quote = self.doc["components"]["schemas"]["Quote"]["properties"]
        for field in ("training_paise", "gst_paise", "total_paise"):
            self.assertEqual(quote[field]["type"], "integer")


if __name__ == "__main__":
    unittest.main()
