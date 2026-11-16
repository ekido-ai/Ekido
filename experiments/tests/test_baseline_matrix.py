"""Focused checks for the baseline matrix's evidence and overwrite guards."""
from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
            with mock.patch.object(matrix.subprocess, 'run') as run:
                with self.assertRaises(FileExistsError):
                    matrix.main(['--recipes-root', str(root), '--out', str(out), '--dry-run'])
                self.assertEqual(run.call_count, len(matrix.RECIPES))  # Validators only; no model command.


if __name__ == '__main__':
    unittest.main()
