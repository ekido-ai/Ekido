"""Audit the fictional clinic FAQ dataset and its deterministic source."""
from __future__ import annotations

import csv
import json
import re
import runpy
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'faq-bot-hinglish'
DEVANAGARI = re.compile(r'[\u0900-\u097f]')


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    data = {split: read(DATA / f'{split}.csv') for split in ('train', 'test')}
    seen: set[str] = set()
    script_counts: dict[str, int] = {}
    for split, rows in data.items():
        expected = 300 if split == 'train' else 60
        if len(rows) != expected:
            raise ValueError(f'{split}: expected {expected} rows, got {len(rows)}')
        script_counts[split] = 0
        for line, row in enumerate(rows, 2):
            if not row['question'].strip() or not row['answer'].strip():
                raise ValueError(f'{split}:{line}: empty question or answer')
            q_deva = bool(DEVANAGARI.search(row['question']))
            a_deva = bool(DEVANAGARI.search(row['answer']))
            if q_deva != a_deva:
                raise ValueError(f'{split}:{line}: question and answer scripts differ')
            script_counts[split] += q_deva
            question = ' '.join(row['question'].casefold().split())
            if question in seen:
                raise ValueError(f'{split}:{line}: duplicated or overlapping question')
            seen.add(question)

    module = runpy.run_path(str(ROOT / 'generate_clinic_faq.py'))
    generate = module['main']
    if len(module['FAQ']) != 20:
        raise ValueError('Expected 20 fictional topics')
    with tempfile.TemporaryDirectory() as tmp:
        generate.__globals__['ROOT'] = Path(tmp)
        generate()
        for split in data:
            if data[split] != read(Path(tmp) / f'{split}.csv'):
                raise ValueError(f'{split}: regenerated rows differ')

    result = {'train_rows': len(data['train']), 'test_rows': len(data['test']), 'fictional_topics': 20,
              'train_questions_with_devanagari': script_counts['train'],
              'test_questions_with_devanagari': script_counts['test'],
              'question_answer_script_mismatches': 0, 'duplicate_or_overlapping_questions': 0,
              'reproduced_from_generator': True}
    out = ROOT.parent / 'results' / 'datasets' / 'faq-bot-hinglish-audit.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
