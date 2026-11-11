"""Needs eth-account. Skipped where it isn't installed, so stdlib-only runs still work."""

import json
import unittest
from pathlib import Path

try:
    from eth_account import Account

    from gpuchain_core.signing import (
        order_signatures,
        recover_document_signer,
        recover_verdict_signer,
        sign_document,
        sign_verdict,
        verdict_digest,
        verify_document,
    )
    import generate_verdict_vector as vector
except ImportError:  # pragma: no cover
    Account = None

KEY_A = "0x" + "11" * 32
KEY_B = "0x" + "22" * 32
VECTOR_FILE = Path(__file__).resolve().parents[3] / "docs" / "schemas" / "vectors" / "verdict_vector.json"


@unittest.skipIf(Account is None, "eth-account not installed")
class Documents(unittest.TestCase):
    doc = {"logical_step": 100, "job_id": "x", "files": {"a": 1}}

    def test_round_trip(self):
        signer, signature = sign_document(self.doc, KEY_A)
        self.assertEqual(signer, Account.from_key(KEY_A).address)
        self.assertTrue(verify_document(self.doc, signature, signer))

    def test_tampered_document_fails(self):
        signer, signature = sign_document(self.doc, KEY_A)
        self.assertFalse(verify_document(dict(self.doc, logical_step=101), signature, signer))

    def test_wrong_signer_fails(self):
        _, signature = sign_document(self.doc, KEY_A)
        self.assertFalse(verify_document(self.doc, signature, Account.from_key(KEY_B).address))

    def test_key_order_and_signature_field_do_not_matter(self):
        signer, signature = sign_document(self.doc, KEY_A)
        reordered = {"files": {"a": 1}, "job_id": "x", "logical_step": 100, "signature": signature}
        self.assertTrue(verify_document(reordered, signature, signer))

    def test_garbage_signature_is_false_not_an_exception(self):
        for bad in ("0x", "0x1234", "nonsense", "0x" + "00" * 65):
            self.assertIsNone(recover_document_signer(self.doc, bad))
            self.assertFalse(verify_document(self.doc, bad, Account.from_key(KEY_A).address))


@unittest.skipIf(Account is None, "eth-account not installed")
class Verdicts(unittest.TestCase):
    verdict = {} if Account is None else vector.VERDICTS["passed_two_payees"]

    def test_signer_recovers(self):
        signature = sign_verdict(self.verdict, 84532, vector.CONTRACT, KEY_A)
        self.assertEqual(recover_verdict_signer(self.verdict, 84532, vector.CONTRACT, signature), Account.from_key(KEY_A).address)

    def test_digest_is_bound_to_chain_contract_and_content(self):
        base = verdict_digest(self.verdict, 84532, vector.CONTRACT)
        self.assertNotEqual(base, verdict_digest(self.verdict, 31337, vector.CONTRACT))
        self.assertNotEqual(base, verdict_digest(self.verdict, 84532, "0x" + "22" * 20))
        self.assertNotEqual(base, verdict_digest(dict(self.verdict, amounts=[2_500_000, 2_000_000]), 84532, vector.CONTRACT))

    def test_order_is_ascending_and_deduplicated(self):
        a = sign_verdict(self.verdict, 84532, vector.CONTRACT, KEY_A)
        b = sign_verdict(self.verdict, 84532, vector.CONTRACT, KEY_B)
        ordered = order_signatures(self.verdict, 84532, vector.CONTRACT, [b, a, a])
        self.assertEqual(len(ordered), 2)
        signers = [int(recover_verdict_signer(self.verdict, 84532, vector.CONTRACT, s), 16) for s in ordered]
        self.assertEqual(signers, sorted(signers))
        self.assertEqual(ordered, order_signatures(self.verdict, 84532, vector.CONTRACT, [a, b]))

    def test_committed_vector_matches_this_code(self):
        self.assertTrue(VECTOR_FILE.exists(), "generate it with tests/generate_verdict_vector.py")
        self.assertEqual(json.loads(VECTOR_FILE.read_text(encoding="utf-8")), vector.build())


if __name__ == "__main__":
    unittest.main()
