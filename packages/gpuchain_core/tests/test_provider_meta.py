import unittest
from decimal import Decimal

from gpuchain_core.provider_meta import metadata_hash, price_micros, provider_metadata

# Shared with apps/web-combined/src/lib/chain/registry.test.ts: both must produce this exact hash.
VECTOR_META = provider_metadata("Vaibhav RTX 4060", "0x00000000000000000000000000000000000000AA", "0.000004", 8192)
VECTOR_JSON = '{"capacity_mib":8192,"kind":"gpuchain.provider_meta.v1","name":"Vaibhav RTX 4060","price_per_step_micros":4,"wallet":"0x00000000000000000000000000000000000000aa"}'


class ProviderMetaTest(unittest.TestCase):
    def test_price_is_whole_micro_usdc(self):
        self.assertEqual(price_micros("0.002"), 2000)
        self.assertEqual(price_micros(Decimal("0.002000")), 2000)
        self.assertEqual(price_micros("1"), 1_000_000)
        for bad in ("0", "-1", "0.0000001"):
            with self.assertRaises(ValueError):
                price_micros(bad)

    def test_formatting_does_not_change_the_hash(self):
        a = provider_metadata(" My GPU ", "0xABCDEF0000000000000000000000000000000001", "0.002", 4096)
        b = provider_metadata("My GPU", "0xabcdef0000000000000000000000000000000001", "0.002000", 4096)
        self.assertEqual(metadata_hash(a), metadata_hash(b))

    def test_any_term_change_changes_the_hash(self):
        base = metadata_hash(provider_metadata("My GPU", "0x" + "1" * 40, "0.002", 4096))
        self.assertNotEqual(base, metadata_hash(provider_metadata("My GPU", "0x" + "1" * 40, "0.003", 4096)))
        self.assertNotEqual(base, metadata_hash(provider_metadata("My GPU 2", "0x" + "1" * 40, "0.002", 4096)))
        self.assertNotEqual(base, metadata_hash(provider_metadata("My GPU", "0x" + "1" * 40, "0.002", None)))

    def test_cross_language_vector(self):
        from gpuchain_core.canonical import canonical_bytes

        self.assertEqual(canonical_bytes(VECTOR_META).decode(), VECTOR_JSON)
        print("vector hash", metadata_hash(VECTOR_META))


if __name__ == "__main__":
    unittest.main()
