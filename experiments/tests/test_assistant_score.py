import importlib.util
import json
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'assistant' / 'score.py'
spec = importlib.util.spec_from_file_location('assistant_score', SCRIPT)
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)


def valid_spec():
    return {'template': 'llm-lora/v1', 'recipe_id': 'review-sentiment',
            'model': {'id': 'Qwen/Qwen2.5-0.5B-Instruct', 'revision': '7ae557604adf67be50417f59c2c2f167def9a775'},
            'dataset': {'sha256': 'b' * 64, 'bytes': 1000, 'train_rows': 30, 'test_rows': 20},
            'lora': {'r': 16, 'alpha': 32, 'dropout': .05, 'target_modules': ['q_proj', 'v_proj']},
            'max_seq_length': 512, 'logical_batch_size': 16, 'total_logical_steps': 200, 'seed': 7,
            'optimizer': {'name': 'adamw', 'lr': .0002, 'weight_decay': 0.0, 'betas': [.9, .999],
                          'eps': 1e-8, 'max_grad_norm': 1.0},
            'lr_schedule': {'name': 'linear_warmup_linear_decay', 'warmup_steps': 10}}


class AssistantScore(unittest.TestCase):
    def test_scores_real_response_shapes_and_exposes_missed_refusals(self):
        cases = [{'prompt': 'synthetic allowed', 'should_refuse': False,
                  'expected': {'recipe': 'review-sentiment', 'language': 'en', 'labels': ['positive', 'negative', 'neutral']}},
                 {'prompt': 'synthetic banned', 'should_refuse': True},
                 {'prompt': 'synthetic review', 'should_refuse': True},
                 {'prompt': 'synthetic unsafe', 'should_refuse': True}]
        replies = iter([
            {'proposal': {'recipe_id': 'review-sentiment', 'dataset_id': 'ds_test',
                          'base_model': 'qwen2.5-0.5b-instruct', 'labels': ['neutral', 'positive', 'negative']},
             'job_spec': valid_spec(), 'language': 'en', 'policy_status': 'model_screened_needs_review'},
            {'refused': 'refuse'}, {'refused': 'review'}, {'refused': 'refuse', 'job_spec': valid_spec()}])
        result = score.evaluate(cases, {'review-sentiment': 'ds_test'}, lambda _: (next(replies), 'a' * 64))
        self.assertTrue(result['complete'])
        self.assertEqual(result['valid_spec_rate'], 1)
        self.assertEqual(result['matched_rate'], 1)
        self.assertFalse(result['all_refused'])
        self.assertEqual([row['result'] for row in result['records']], ['valid', 'refused', 'review', 'missed_refusal'])
        self.assertNotIn('synthetic allowed', json.dumps(result))

    def test_missing_mappings_and_transport_failures_do_not_claim_success(self):
        cases = [{'prompt': 'one', 'should_refuse': False,
                  'expected': {'recipe': 'review-sentiment', 'language': 'en'}}]
        calls = []
        with self.assertRaises(ValueError):
            score.evaluate(cases, {}, lambda body: calls.append(body))
        self.assertEqual(calls, [])
        def fail(_):
            raise OSError('offline')
        result = score.evaluate(cases, {'review-sentiment': 'ds_test'}, fail)
        self.assertFalse(result['complete'])
        self.assertIsNone(result['valid_spec_rate'])
        self.assertIsNone(result['all_refused'])

    def test_wrong_model_revision_is_not_counted_as_a_valid_spec(self):
        case = {'prompt': 'one', 'should_refuse': False,
                'expected': {'recipe': 'review-sentiment', 'language': 'en'}}
        altered = valid_spec()
        altered['model']['revision'] = 'f' * 40
        response = {'proposal': {'recipe_id': 'review-sentiment', 'dataset_id': 'ds_test',
                    'base_model': 'qwen2.5-0.5b-instruct'}, 'job_spec': altered,
                    'language': 'en', 'policy_status': 'model_screened_needs_review'}
        result = score.evaluate([case], {'review-sentiment': 'ds_test'}, lambda _: (response, 'a' * 64))
        self.assertEqual(result['valid_specs'], 0)
        self.assertFalse(result['valid_spec_target_met'])

    def test_http_requires_loopback_and_no_credentials(self):
        self.assertTrue(score.endpoint('http://127.0.0.1:8010').endswith('/v1/assistant/messages'))
        for url in ('http://example.com', 'https://user:pass@example.com', 'https://example.com?q=key'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                score.endpoint(url)


if __name__ == '__main__':
    unittest.main()
