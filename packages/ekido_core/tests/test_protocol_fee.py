import unittest
from decimal import Decimal

from ekido_core.protocol_fee import add_fee, fee_amount, fee_problems, fee_terms, provider_budget

TREASURY = "0x915f91f109980C5E810507feD50d5D364d15E074"
A = "0x00000000000000000000000000000000000000aa"
B = "0x00000000000000000000000000000000000000bb"


class ProtocolFeeTest(unittest.TestCase):
    def test_terms_are_validated(self):
        self.assertEqual(fee_problems({}), [])
        self.assertEqual(fee_problems({"protocol_fee": {"bps": 800, "recipient": TREASURY}}), [])
        self.assertTrue(fee_problems({"protocol_fee": {"bps": 2001, "recipient": TREASURY}}))
        self.assertTrue(fee_problems({"protocol_fee": {"bps": 8.0, "recipient": TREASURY}}))
        self.assertTrue(fee_problems({"protocol_fee": {"bps": 800, "recipient": "0x" + "0" * 40}}))
        self.assertTrue(fee_problems({"protocol_fee": {"bps": 800, "recipient": TREASURY, "extra": 1}}))
        self.assertEqual(fee_terms({"protocol_fee": {"bps": 800, "recipient": TREASURY}}), (800, TREASURY.lower()))

    def test_the_fee_always_fits_the_budget(self):
        budget = Decimal("1")
        cap = provider_budget(budget, 800)
        self.assertEqual(cap, Decimal("0.925925"))
        payouts, refund = add_fee({A: cap}, budget, (800, TREASURY))
        self.assertEqual(payouts[TREASURY.lower()], Decimal("0.074074"))
        self.assertGreaterEqual(refund, 0)
        self.assertEqual(sum(payouts.values()) + refund, budget)

    def test_the_real_settlement_shape(self):
        # 0.12 to one provider out of a 0.15 budget: the fee is 8% of 0.12, the rest goes back.
        payouts, refund = add_fee({A: Decimal("0.12")}, Decimal("0.15"), (800, TREASURY))
        self.assertEqual(payouts, {A: Decimal("0.12"), TREASURY.lower(): Decimal("0.0096")})
        self.assertEqual(refund, Decimal("0.0204"))

    def test_rounding_goes_down_to_micro_usdc(self):
        self.assertEqual(fee_amount(Decimal("0.000012"), 800), Decimal("0.000000"))
        self.assertEqual(fee_amount(Decimal("0.000013"), 800), Decimal("0.000001"))

    def test_no_fee_without_terms_or_without_work(self):
        self.assertEqual(add_fee({A: Decimal("0.1")}, Decimal("0.2"), None), ({A: Decimal("0.1")}, Decimal("0.1")))
        self.assertEqual(add_fee({}, Decimal("0.2"), (800, TREASURY)), ({}, Decimal("0.2")))

    def test_a_recipient_that_is_also_a_provider_is_merged(self):
        payouts, _ = add_fee({A: Decimal("0.1"), B: Decimal("0.1")}, Decimal("1"), (1000, A))
        self.assertEqual(payouts[A], Decimal("0.12"))

    def test_overspending_is_refused(self):
        with self.assertRaises(ValueError):
            add_fee({A: Decimal("1")}, Decimal("1"), (800, TREASURY))

    def test_one_wallet_in_two_casings_is_added_up(self):
        payouts, refund = add_fee({A.upper().replace("0X", "0x"): Decimal("1"), A: Decimal("2")}, Decimal("10"), None)
        self.assertEqual(payouts, {A: Decimal("3")})
        self.assertEqual(refund, Decimal("7"))

    def test_a_negative_payout_is_refused(self):
        with self.assertRaises(ValueError):
            add_fee({A: Decimal("-5"), B: Decimal("5")}, Decimal("5"), None)


if __name__ == "__main__":
    unittest.main()
