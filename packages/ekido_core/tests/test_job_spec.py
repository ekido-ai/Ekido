import unittest

from ekido_core.job_spec import policy_problems, spec_problems

COMMON = {
    "logical_batch_size": 32,
    "total_logical_steps": 400,
    "seed": 1337,
    "optimizer": {"name": "adamw", "lr": 5e-4, "weight_decay": 0.01, "betas": [0.9, 0.999], "eps": 1e-8, "max_grad_norm": 1.0},
    "lr_schedule": {"name": "linear_warmup_linear_decay", "warmup_steps": 40},
}
SYNTHETIC = {**COMMON, "template": "synthetic-linear/v1"}
REAL = {
    **COMMON,
    "template": "distilbert-lora-agnews/v1",
    "model": {"id": "distilbert-base-uncased", "revision": "main"},
    "dataset": {"id": "fancyzhx/ag_news", "split": "train", "fingerprint": "0" * 64},
    "lora": {"r": 8, "alpha": 16, "dropout": 0.1, "target_modules": ["q_lin", "v_lin"]},
    "max_seq_length": 128,
}


class SpecProblems(unittest.TestCase):
    def test_non_object_specs_are_refused_without_crashing(self):
        for value in (None, True, 1, "text", [], [1]):
            with self.subTest(value=value):
                self.assertEqual(spec_problems(value), ["spec must be a JSON object"])

    def test_unhashable_recipe_ids_are_refused_without_crashing(self):
        for value in ([], {}, ["review-sentiment"]):
            with self.subTest(value=value):
                problems = spec_problems({**SYNTHETIC, "template": "llm-lora/v1", "recipe_id": value})
                self.assertTrue(any(problem.startswith("recipe_id must be one of") for problem in problems))

    def test_complete_specs_pass(self):
        self.assertEqual(spec_problems(SYNTHETIC), [])
        self.assertEqual(spec_problems(REAL), [])

    def test_unknown_template_is_refused(self):
        self.assertIn("template", spec_problems({**REAL, "template": "run-my-code/v1"})[0])

    def test_a_real_workload_needs_its_model_and_data(self):
        problems = spec_problems({**COMMON, "template": "distilbert-lora-agnews/v1"})
        for expected in ("model is missing", "dataset is missing", "lora is missing"):
            self.assertIn(expected, problems)

    def test_the_short_form_body_is_refused_with_every_reason(self):
        body = {"template": "distilbert-lora-agnews/v1", "logical_batch_size": 32, "total_logical_steps": 300, "learning_rate": 0.0005, "seed": 1337}
        problems = spec_problems(body)
        self.assertIn("optimizer is missing", problems)
        self.assertIn("lr_schedule is missing", problems)
        self.assertIn("max_seq_length must be a whole number of at least 8", problems)

    def test_bad_numbers_are_refused(self):
        for field, value in (("total_logical_steps", 0), ("logical_batch_size", "32"), ("seed", -1), ("seed", True), ("checkpoint_every_steps", 0)):
            self.assertTrue(spec_problems({**SYNTHETIC, field: value}), f"{field}={value!r}")

    def test_missing_nested_field_is_named(self):
        optimizer = {k: v for k, v in COMMON["optimizer"].items() if k != "lr"}
        self.assertEqual(spec_problems({**SYNTHETIC, "optimizer": optimizer}), ["optimizer.lr is missing"])


class PolicyProblems(unittest.TestCase):
    def test_names_what_verifiers_need(self):
        self.assertIn("policy.eval_set_hash is missing", policy_problems({"metric": "accuracy"}))
        complete = {"min_absolute": 0.88, "non_inferiority_margin": 0.02, "confidence": 0.95, "bootstrap_resamples": 2000, "eval_set_hash": "a", "eval_version_hash": "b"}
        self.assertEqual(policy_problems(complete), [])

    def test_mid_training_margin_stays_in_a_sensible_range(self):
        base = {"min_absolute": 0.88, "non_inferiority_margin": 0.02, "confidence": 0.95, "bootstrap_resamples": 2000, "eval_set_hash": "a", "eval_version_hash": "b"}
        self.assertEqual(policy_problems(dict(base, probation_margin=0.05)), [])
        for bad in (0.01, 0.5):
            self.assertEqual(len(policy_problems(dict(base, probation_margin=bad))), 1, bad)


if __name__ == "__main__":
    unittest.main()
