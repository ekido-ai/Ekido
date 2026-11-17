"""Run the ten recipe/model baselines after checking all five datasets.

Datasets must already exist under --recipes-root, normally after their PRs are
reviewed. --runtime-path points to the separate ekido-workers/runtime checkout.
A dry run validates inputs and prints commands without loading models
or producing result files. Real runs require CUDA. Existing results are never
overwritten. --resume reuses only results with matching dataset, model and code
fingerprints; an incomplete or stale result must be moved aside before retrying.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'packages' / 'ekido_core'))
from ekido_core.recipes import eval_set_hash, recipe  # noqa: E402

RECIPES = ('ticket-sorter-hinglish', 'invoice-fields', 'product-descriptions',
           'faq-bot-hinglish', 'review-sentiment')
MODEL_REVISIONS = {
    'Qwen/Qwen2.5-0.5B-Instruct': '7ae557604adf67be50417f59c2c2f167def9a775',
    'Qwen/Qwen2.5-1.5B-Instruct': '989aa7980e4cf806f80c7fef2b1adb7bc71aa306',
}


def result_path(out: Path, recipe_id: str, model: str) -> Path:
    return out / f"{recipe_id}-{model.rsplit('/', 1)[-1].lower()}.json"


def check_result(path: Path, recipe_id: str, model: str, revision: str,
                 rows: list[dict[str, str]], code_sha256: dict[str, str] | None = None) -> None:
    """Reject incomplete, stale or non-CUDA output from a baseline run."""
    result = json.loads(path.read_text(encoding='utf-8'))
    expected = {'recipe_id': recipe_id, 'model': model, 'model_revision': revision,
                'device': 'cuda', 'metric': recipe(recipe_id).metric, 'examples': len(rows),
                'eval_set_hash': eval_set_hash(recipe_id, rows)}
    if code_sha256 is not None:
        expected.update(max_seq_length=512, code_sha256=code_sha256)
    for key, value in expected.items():
        if result.get(key) != value:
            raise ValueError(f'{path}: {key} does not match the planned run')
    for key in ('score', 'pass_rate'):
        value = result.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f'{path}: invalid {key}')
    timestamp = datetime.fromisoformat(result['run_at'])
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError(f'{path}: run_at must include a timezone')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipes-root', type=Path, default=ROOT / 'experiments' / 'recipes')
    parser.add_argument('--out', type=Path, default=ROOT / 'experiments' / 'results' / 'baselines')
    parser.add_argument('--runtime-path', type=Path, default=ROOT.parent / 'ekido-workers' / 'runtime',
                        help='path to the runtime directory in an ekido-workers checkout')
    parser.add_argument('--dry-run', action='store_true', help='validate inputs and show commands without generating scores')
    parser.add_argument('--resume', action='store_true', help='reuse matching completed results without overwriting them')
    args = parser.parse_args(argv)
    source = args.recipes_root.resolve()
    out = args.out.resolve()
    validator = ROOT / 'experiments' / 'recipes' / 'validate_dataset.py'
    baseline = ROOT / 'experiments' / 'recipes' / 'baseline.py'

    # Fail before starting expensive work if any dataset is missing or invalid.
    rows_by_recipe = {}
    for recipe_id in RECIPES:
        folder = source / recipe_id
        subprocess.run([sys.executable, '-I', str(validator), str(folder)], check=True)
        with (folder / 'test.csv').open(encoding='utf-8', newline='') as handle:
            rows_by_recipe[recipe_id] = list(csv.DictReader(handle))

    jobs = [(name, model, revision, result_path(out, name, model))
            for name in RECIPES for model, revision in MODEL_REVISIONS.items()]
    existing = [str(target) for _, _, _, target in jobs if target.exists()]
    if existing and not args.resume:
        raise FileExistsError('Refusing to overwrite existing result files; choose a new --out: ' + ', '.join(existing))
    runtime = args.runtime_path.resolve()
    if not (runtime / 'ekido_runtime' / 'llm.py').is_file():
        parser.error(f'--runtime-path must contain ekido_runtime/llm.py: {runtime}')
    code_sha256 = {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in {
        'baseline': baseline, 'recipes': ROOT / 'packages' / 'ekido_core' / 'ekido_core' / 'recipes.py',
        'runtime': runtime / 'ekido_runtime' / 'llm.py'}.items()}
    # Verify every existing result before launching any costly job.
    if args.resume:
        for name, model, revision, target in jobs:
            if target.exists():
                check_result(target, name, model, revision, rows_by_recipe[name], code_sha256)
    pending = [(name, model, revision, target) for name, model, revision, target in jobs if not target.exists()]
    for name, model, revision, target in pending:
        if not re.fullmatch(r'[0-9a-f]{40}', revision):
            raise ValueError(f'Invalid pinned revision for {model}')
        command = [sys.executable, '-I', str(baseline), str(source / name), '--model', model,
                   '--revision', revision, '--device', 'cuda', '--runtime-path', str(runtime), '--out', str(out)]
        print(shlex.join(command), flush=True)
        if not args.dry_run:
            subprocess.run(command, check=True)
            check_result(target, name, model, revision, rows_by_recipe[name], code_sha256)
    print(f'{len(pending)} commands ' + ('planned; no model was run.' if args.dry_run else 'completed and verified.')
          + (f' {len(jobs) - len(pending)} matching results reused.' if args.resume else ''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
