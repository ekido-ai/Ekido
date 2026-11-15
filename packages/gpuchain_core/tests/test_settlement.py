import unittest
from decimal import Decimal

from gpuchain_core.settlement import ZERO_BYTES32, build_verdict, lineage_root, quality_report_root, to_base_units, to_bytes32

A = "0x00000000000000000000000000000000000000A1"
B = "0x00000000000000000000000000000000000000B2"
JOB = "0x" + "ab" * 32
H1, H2, H3 = "1" * 64, "2" * 64, "3" * 64
REPORT_1 = {"verdict": "PASS", "device": "cuda", "signer": A}
REPORT_2 = {"verdict": "PASS", "device": "cpu", "signer": B}


def verdict(**overrides):
    args = dict(
        onchain_job_id=JOB, passed=True, final_checkpoint_hash=H2, lineage=[H1, H2], reports=[REPORT_1, REPORT_2],
        payouts={A: Decimal("2"), B: Decimal("2.5")}, refund=Decimal("0.5"), budget=Decimal("5"), expiry=1_900_000_000,
    )
    return build_verdict(**(args | overrides))


class Bytes32(unittest.TestCase):
    def test_whitespace_cannot_stand_in_for_hex_digits(self):
        # Sixty-two hex digits plus two spaces is 64 characters, and bytes.fromhex skips the spaces.
        for value in ("aa" * 31 + "  ", " " + "aa" * 31 + " ", "aa" * 31 + "\n\n"):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValueError):
                    to_bytes32(value)

    def test_a_valid_digest_is_lowercased_and_prefixed(self):
        self.assertEqual(to_bytes32("AB" * 32), "0x" + "ab" * 32)


class Roots(unittest.TestCase):
    def test_lineage_depends_on_order(self):
        self.assertNotEqual(lineage_root([H1, H2]), lineage_root([H2, H1]))

    def test_lineage_depends_on_content(self):
        self.assertNotEqual(lineage_root([H1, H2]), lineage_root([H1, H3]))

    def test_empty_lineage_refused(self):
        with self.assertRaises(ValueError):
            lineage_root([])

    def test_report_order_does_not_matter(self):
        self.assertEqual(quality_report_root([REPORT_1, REPORT_2]), quality_report_root([REPORT_2, REPORT_1]))

    def test_duplicate_report_does_not_matter(self):
        self.assertEqual(quality_report_root([REPORT_1, REPORT_1, REPORT_2]), quality_report_root([REPORT_1, REPORT_2]))

    def test_signature_does_not_change_report_hash(self):
        signed = dict(REPORT_1, signature="0xaa")
        self.assertEqual(quality_report_root([signed]), quality_report_root([REPORT_1]))

    def test_different_reports_differ(self):
        self.assertNotEqual(quality_report_root([REPORT_1]), quality_report_root([REPORT_2]))

    def test_no_reports_refused(self):
        with self.assertRaises(ValueError):
            quality_report_root([])

    def test_lineage_and_report_domains_are_separate(self):
        self.assertNotEqual(lineage_root([H1]), quality_report_root([{"manifests": [H1]}]))

    def test_bytes32_format(self):
        self.assertEqual(to_bytes32("A" * 64), "0x" + "a" * 64)
        for bad in ("abc", "g" * 64):
            with self.assertRaises(ValueError):
                to_bytes32(bad)


class Units(unittest.TestCase):
    def test_conversion(self):
        self.assertEqual(to_base_units(Decimal("2.5")), 2_500_000)
        self.assertEqual(to_base_units(Decimal("0.000001")), 1)

    def test_sub_unit_amount_refused_not_rounded(self):
        with self.assertRaises(ValueError):
            to_base_units(Decimal("0.0000001"))


class Verdicts(unittest.TestCase):
    def test_every_verifier_derives_the_same_verdict(self):
        a = verdict(reports=[REPORT_1, REPORT_2], payouts={A: Decimal("2"), B: Decimal("2.5")})
        b = verdict(reports=[REPORT_2, REPORT_1], payouts={B: Decimal("2.5"), A: Decimal("2")})
        self.assertEqual(a, b)

    def test_shape_matches_the_contract(self):
        v = verdict()
        self.assertEqual(v["payees"], [A, B])
        self.assertEqual(v["amounts"], [2_000_000, 2_500_000])
        self.assertEqual(v["refund"], 500_000)
        self.assertEqual(v["finalCheckpoint"], "0x" + H2)
        self.assertEqual(sum(v["amounts"]) + v["refund"], 5_000_000)

    def test_payees_sorted_numerically(self):
        self.assertEqual(verdict(payouts={B: Decimal("1"), A: Decimal("3.5")})["payees"], [A, B])

    def test_zero_payouts_are_dropped(self):
        v = verdict(payouts={A: Decimal("4.5"), B: Decimal("0")})
        self.assertEqual(v["payees"], [A])

    def test_wrong_total_refused(self):
        with self.assertRaises(ValueError):
            verdict(refund=Decimal("0.4"))

    def test_failed_verdict_refunds_fully(self):
        v = verdict(passed=False, final_checkpoint_hash=None, lineage=[], payouts={}, refund=Decimal("5"))
        self.assertEqual((v["payees"], v["amounts"], v["refund"]), ([], [], 5_000_000))
        self.assertEqual((v["finalCheckpoint"], v["lineageRoot"]), (ZERO_BYTES32, ZERO_BYTES32))

    def test_failed_verdict_cannot_pay_anyone(self):
        with self.assertRaises(ValueError):
            verdict(passed=False)

    def test_too_many_payees_refused(self):
        payouts = {f"0x{i:040x}": Decimal("0.5") for i in range(1, 10)}
        with self.assertRaises(ValueError):
            verdict(payouts=payouts, refund=Decimal("0.5"))

    def test_a_negative_refund_is_refused(self):
        with self.assertRaises(ValueError):
            verdict(payouts={A: Decimal("6")}, refund=Decimal("-1"), budget=Decimal("5"))

    def test_a_negative_payout_is_refused(self):
        with self.assertRaises(ValueError):
            verdict(payouts={A: Decimal("-1"), B: Decimal("5")}, refund=Decimal("0"), budget=Decimal("5"))


if __name__ == "__main__":
    unittest.main()
