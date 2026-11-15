"""Recipes (prompt format and scoring) and the llm-lora/v1 spec rules."""
import json
import unittest

from ekido_core.job_spec import LLM_BASES, spec_problems
from ekido_core.recipes import RECIPES, recipe, rouge_l, score, score_one

COMMIT = "a" * 40
DIGEST = "b" * 64


def llm_spec(**overrides):
    spec = {
        "template": "llm-lora/v1",
        "recipe_id": "ticket-sorter-hinglish",
        "model": {"id": LLM_BASES[0], "revision": COMMIT},
        "dataset": {"sha256": DIGEST, "train_rows": 500, "test_rows": 100},
        "lora": {"r": 16, "alpha": 32, "dropout": 0.05, "target_modules": ["q_proj", "v_proj"]},
        "max_seq_length": 256,
        "logical_batch_size": 16,
        "total_logical_steps": 200,
        "seed": 7,
        "optimizer": {"name": "adamw", "lr": 2e-4, "weight_decay": 0.0, "betas": [0.9, 0.999], "eps": 1e-8, "max_grad_norm": 1.0},
        "lr_schedule": {"name": "linear", "warmup_steps": 10},
    }
    spec.update(overrides)
    return spec


class Recipes(unittest.TestCase):
    def test_five_recipes_with_their_columns_match_the_dataset_checker(self):
        self.assertEqual(
            {k: r.columns for k, r in RECIPES.items()},
            {
                "ticket-sorter-hinglish": ("text", "label"),
                "invoice-fields": ("text", "json"),
                "product-descriptions": ("attributes", "description"),
                "faq-bot-hinglish": ("question", "answer"),
                "review-sentiment": ("text", "label"),
            },
        )

    def test_a_row_becomes_a_prompt_and_a_completion(self):
        example = recipe("ticket-sorter-hinglish").example({"text": "  Mera order abhi tak nahi aaya ", "label": "complaint"})
        self.assertTrue(example["prompt"].endswith("Ticket: Mera order abhi tak nahi aaya\nCategory:"))
        self.assertEqual(example["completion"], " complaint")

    def test_classification_takes_the_first_allowed_label(self):
        self.assertEqual(score_one("ticket-sorter-hinglish", "Refund hai ye, order nahi", "refund"), 1.0)
        self.assertEqual(score_one("ticket-sorter-hinglish", "I think it's a question", "refund"), 0.0)
        self.assertEqual(score_one("review-sentiment", "", "neutral"), 0.0)

    def test_invoice_fields_score_per_field(self):
        want = json.dumps({"vendor": "Sharma Traders", "invoice_no": "INV-7", "date": "2026-11-01", "total": "1180", "gstin": "27ABCDE1234F1Z5"})
        got = 'Here: {"vendor": "sharma traders", "invoice_no": "INV-7", "date": "2026-11-02", "total": "1180", "gstin": "27ABCDE1234F1Z5"}'
        self.assertAlmostEqual(score_one("invoice-fields", got, want), 0.8)
        self.assertEqual(score_one("invoice-fields", "not json", want), 0.0)

    def test_rouge_l(self):
        self.assertEqual(rouge_l("a soft cotton kurta", "a soft cotton kurta"), 1.0)
        self.assertEqual(rouge_l("", "anything"), 0.0)
        self.assertGreater(rouge_l("soft cotton kurta for summer", "a soft cotton kurta"), 0.5)

    def test_mean_score_and_bad_input(self):
        self.assertEqual(score("review-sentiment", ["positive", "negative"], ["positive", "neutral"]), 0.5)
        with self.assertRaises(ValueError):
            score("review-sentiment", ["positive"], [])
        with self.assertRaises(ValueError):
            recipe("make-me-rich")

    def test_plain_words(self):
        self.assertEqual(recipe("ticket-sorter-hinglish").plain_words(100), "At least 80% of your 100 test examples answered correctly")


class LlmSpec(unittest.TestCase):
    def test_a_good_spec_passes(self):
        self.assertEqual(spec_problems(llm_spec()), [])

    def test_only_licence_checked_bases(self):
        problems = spec_problems(llm_spec(model={"id": "Qwen/Qwen2.5-3B-Instruct", "revision": COMMIT}))
        self.assertTrue(any("model.id must be one of" in p for p in problems))

    def test_pinned_revision_and_dataset_fingerprint(self):
        problems = spec_problems(llm_spec(model={"id": LLM_BASES[1], "revision": "main"}, dataset={"sha256": "nope", "train_rows": 500, "test_rows": 5}))
        joined = "\n".join(problems)
        self.assertIn("model.revision", joined)
        self.assertIn("dataset.sha256", joined)
        self.assertIn("test_rows", joined)

    def test_recipe_and_length(self):
        joined = "\n".join(spec_problems(llm_spec(recipe_id="x", max_seq_length=10_000)))
        self.assertIn("recipe_id must be one of", joined)
        self.assertIn("max_seq_length", joined)

    def test_missing_sections(self):
        spec = llm_spec()
        del spec["lora"]
        self.assertIn("lora is missing", spec_problems(spec))


if __name__ == "__main__":
    unittest.main()
