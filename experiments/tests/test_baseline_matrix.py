"""Focused checks for the baseline matrix's evidence and overwrite guards."""
from __future__ import annotations

import csv
import contextlib
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('run_baseline_matrix', HERE / 'recipes' / 'run_baseline_matrix.py')
matrix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(matrix)


class BaselineMatrixTest(unittest.TestCase):
    def setUp(self) -> None:
        self.recipe_id = 'review-sentiment'
        self.model, self.revision = next(iter(matrix.MODEL_REVISIONS.items()))
        self.rows = [{'text': 'A useful item', 'label': 'positive'}]
        self.result = {'recipe_id': self.recipe_id, 'model': self.model, 'model_revision': self.revision,
                       'device': 'cuda', 'metric': 'accuracy', 'examples': 1,
                       'eval_set_hash': matrix.eval_set_hash(self.recipe_id, self.rows),
                       'score': 1.0, 'pass_rate': 1.0, 'run_at': '2026-11-16T12:00:00+00:00'}

    def test_result_guard_rejects_stale_or_invalid_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'result.json'
            path.write_text(json.dumps(self.result), encoding='utf-8')
            matrix.check_result(path, self.recipe_id, self.model, self.revision, self.rows)
            for key, value in [('eval_set_hash', 'wrong'), ('device', 'cpu'), ('score', 2),
                               ('pass_rate', float('nan')), ('run_at', '2026-11-16T12:00:00')]:
                with self.subTest(key=key):
                    changed = {**self.result, key: value}
                    path.write_text(json.dumps(changed), encoding='utf-8')
                    with self.assertRaises(ValueError):
                        matrix.check_result(path, self.recipe_id, self.model, self.revision, self.rows)

    def test_existing_result_stops_before_any_model_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'inputs'
            for name in matrix.RECIPES:
                folder = root / name
                folder.mkdir(parents=True)
                columns = matrix.recipe(name).columns
                with (folder / 'test.csv').open('w', encoding='utf-8', newline='') as handle:
                    writer = csv.DictWriter(handle, fieldnames=columns)
                    writer.writeheader()
                    writer.writerow(dict.fromkeys(columns, 'example'))
            out = Path(temp) / 'results'
            out.mkdir()
            matrix.result_path(out, self.recipe_id, self.model).write_text('existing', encoding='utf-8')
            with unittest.mock.patch.object(matrix.subprocess, 'run') as run:
                with self.assertRaises(FileExistsError):
                    matrix.main(['--recipes-root', str(root), '--out', str(out), '--dry-run'])
                self.assertEqual(run.call_count, len(matrix.RECIPES))  # Validators only; no model command.

    def test_split_runtime_is_checked_and_passed_to_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'inputs'
            for name in matrix.RECIPES:
                folder = root / name
                folder.mkdir(parents=True)
                columns = matrix.recipe(name).columns
                with (folder / 'test.csv').open('w', encoding='utf-8', newline='') as handle:
                    writer = csv.DictWriter(handle, fieldnames=columns)
                    writer.writeheader()
                    writer.writerow(dict.fromkeys(columns, 'example'))
            runtime = Path(temp) / 'workers' / 'runtime'
            args = ['--recipes-root', str(root), '--runtime-path', str(runtime), '--dry-run']
            with unittest.mock.patch.object(matrix.subprocess, 'run'), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    matrix.main(args)
                (runtime / 'ekido_runtime').mkdir(parents=True)
                (runtime / 'ekido_runtime' / 'llm.py').touch()
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(matrix.main(args), 0)
                self.assertEqual(output.getvalue().count('--runtime-path'), 10)

    def test_resume_validates_every_existing_result_before_planning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'inputs'
            for name in matrix.RECIPES:
                folder = root / name
                folder.mkdir(parents=True)
                columns = matrix.recipe(name).columns
                with (folder / 'test.csv').open('w', encoding='utf-8', newline='') as handle:
                    writer = csv.DictWriter(handle, fieldnames=columns)
                    writer.writeheader()
                    writer.writerow(dict.fromkeys(columns, 'example'))
            runtime_file = Path(temp) / 'runtime' / 'ekido_runtime' / 'llm.py'
            runtime_file.parent.mkdir(parents=True)
            runtime_file.write_text('# runtime\n', encoding='utf-8')
            out = Path(temp) / 'results'
            out.mkdir()
            rows = [dict.fromkeys(matrix.recipe(self.recipe_id).columns, 'example')]
            hashes = {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in {
                'baseline': matrix.ROOT / 'experiments' / 'recipes' / 'baseline.py',
                'recipes': matrix.ROOT / 'packages' / 'ekido_core' / 'ekido_core' / 'recipes.py',
                'runtime': runtime_file}.items()}
            result = {**self.result, 'eval_set_hash': matrix.eval_set_hash(self.recipe_id, rows),
                      'max_seq_length': 512, 'code_sha256': hashes}
            target = matrix.result_path(out, self.recipe_id, self.model)
            target.write_text(json.dumps(result), encoding='utf-8')
            args = ['--recipes-root', str(root), '--out', str(out), '--runtime-path',
                    str(runtime_file.parent.parent), '--resume', '--dry-run']
            with unittest.mock.patch.object(matrix.subprocess, 'run') as run:
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(matrix.main(args), 0)
                self.assertIn('9 commands planned', output.getvalue())
                self.assertIn('1 matching results reused', output.getvalue())
                self.assertEqual(run.call_count, len(matrix.RECIPES))
                target.write_text(json.dumps({**result, 'code_sha256': {**hashes, 'runtime': 'stale'}}), encoding='utf-8')
                run.reset_mock()
                with contextlib.redirect_stdout(io.StringIO()) as output, self.assertRaises(ValueError):
                    matrix.main(args)
                self.assertEqual(output.getvalue(), '')
                self.assertEqual(run.call_count, len(matrix.RECIPES))


if __name__ == '__main__':
    unittest.main()
