"""Quotes: the price arithmetic, GST, the plan, and that an issued quote can't be altered."""
import unittest
from datetime import datetime, timedelta, timezone

from ekido_core.job_spec import LLM_BASES
from ekido_core.quotes import DEFAULT_PRICES, QUOTE_VALID_FOR, QuoteError, gst, make_quote, rupees, training_plan, verify_quote

NOW = datetime(2026, 11, 17, 10, 0, tzinfo=timezone.utc)
SMALL, LARGE = LLM_BASES


def quote(**overrides):
    args = dict(recipe_id="ticket-sorter-hinglish", base_model=SMALL, train_rows=500, test_rows=100, dataset_sha256="b" * 64, now=NOW)
    args.update(overrides)
    return make_quote(**args)


class Quotes(unittest.TestCase):
    def test_gst_is_18_percent_rounded_half_up(self):
        self.assertEqual(gst(10_000), 1_800)
        self.assertEqual(gst(9_900), 1_782)
        self.assertEqual(gst(25), 5)   # 4.5 paise rounds up
        self.assertEqual(gst(24), 4)   # 4.32 rounds down
        self.assertEqual(gst(0), 0)

    def test_a_small_job_pays_the_minimum(self):
        q = quote()
        # 500 rows x 256 tokens x 3 epochs = 384,000 tokens; at 4,000 paise per million that is 1,536 paise, under the minimum.
        self.assertEqual(q["plan"]["total_logical_steps"], 94)  # ceil(1500 / 16)
        self.assertEqual(q["compute_paise"], DEFAULT_PRICES.minimum_job)
        self.assertEqual(q["total_paise"], q["training_paise"] + q["gst_paise"])
        self.assertEqual(q["gst_paise"], gst(q["training_paise"]))

    def test_price_grows_with_rows_and_model_size(self):
        big = quote(train_rows=20_000)
        self.assertEqual(big["compute_paise"], 61_440)  # 20,000 x 256 x 3 = 15.36M tokens x 4,000 paise
        self.assertGreater(quote(train_rows=20_000, base_model=LARGE)["compute_paise"], big["compute_paise"])
        self.assertGreater(big["eta_minutes"], quote()["eta_minutes"])

    def test_the_fee_comes_out_of_the_price_not_on_top(self):
        q = quote(train_rows=20_000)
        self.assertEqual(q["ekido_fee_paise"], 6_144)
        self.assertEqual(q["ekido_fee_paise"] + q["provider_budget_paise"], q["training_paise"])

    def test_distillation_tops_up_to_the_target_and_is_priced_per_generated_row(self):
        q = quote(train_rows=30, distill=True)
        self.assertEqual((q["plan"]["train_rows"], q["plan"]["generated_rows"]), (1000, 970))
        self.assertEqual(q["distillation_paise"], 970 * DEFAULT_PRICES.per_distilled_row)
        self.assertEqual(training_plan("ticket-sorter-hinglish", 5000, distill=True)["generated_rows"], 0)

    def test_quality_terms_come_from_the_recipe_in_plain_words(self):
        terms = quote()["quality_terms"]
        self.assertEqual(terms["plain_words"], "At least 80% of your 100 test examples answered correctly; the model must also perform better than the untrained base on the same examples")
        self.assertIn("does not beat the untrained base", quote()["refund_policy"])
        self.assertEqual(quote(recipe_id="invoice-fields")["plan"]["max_seq_length"], 768)

    def test_prices_are_flagged_provisional(self):
        self.assertIs(quote()["prices_provisional"], True)

    def test_an_issued_quote_cant_be_altered_and_expires(self):
        q = quote()
        verify_quote(q, now=NOW + timedelta(minutes=5))
        cheaper = dict(q, total_paise=1)
        with self.assertRaises(QuoteError):
            verify_quote(cheaper, now=NOW)
        with self.assertRaises(QuoteError):
            verify_quote(q, now=NOW + QUOTE_VALID_FOR)

    def test_same_inputs_same_hash(self):
        self.assertEqual(quote()["terms_hash"], quote()["terms_hash"])
        self.assertNotEqual(quote()["terms_hash"], quote(train_rows=501)["terms_hash"])

    def test_bad_requests_are_refused_with_a_reason(self):
        for bad in (dict(base_model="Qwen/Qwen2.5-3B-Instruct"), dict(test_rows=5), dict(train_rows=0), dict(hosting_requests_per_month=-1), dict(recipe_id="x")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                quote(**bad)

    def test_rupees_use_indian_grouping(self):
        self.assertEqual(rupees(11_682), "₹116.82")
        self.assertEqual(rupees(12_345_678), "₹1,23,456.78")
        self.assertEqual(rupees(100_000_000), "₹10,00,000.00")
        self.assertEqual(rupees(5), "₹0.05")
        self.assertEqual(rupees(-9_900), "-₹99.00")


if __name__ == "__main__":
    unittest.main()
