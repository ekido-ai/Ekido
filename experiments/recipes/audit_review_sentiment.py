"""Audit synthetic review labels, split separation and reproducibility."""
from __future__ import annotations

import csv
import difflib
import json
import re
import runpy
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'review-sentiment'
DEVANAGARI = re.compile(r'[\u0900-\u097f]')
EXPECTED = {'train': {'positive': 167, 'negative': 167, 'neutral': 166},
            'test': {'positive': 34, 'negative': 33, 'neutral': 33}}


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    data = {split: read(DATA / f'{split}.csv') for split in ('train', 'test')}
    module = runpy.run_path(str(ROOT / 'generate_review_sentiment.py'))
    seen: set[str] = set()
    scripts = {}
    for split, rows in data.items():
        if Counter(row['label'] for row in rows) != EXPECTED[split]:
            raise ValueError(f'{split}: unexpected label distribution')
        patterns = module['TRAIN' if split == 'train' else 'TEST']
        allowed = {}
        for label, templates in patterns.items():
            for template in templates:
                for product in module['PRODUCTS']:
                    text = template.format(product=product)
                    if text in allowed and allowed[text] != label:
                        raise ValueError(f'{split}: template assigned to multiple labels')
                    allowed[text] = label
        scripts[split] = 0
        for line, row in enumerate(rows, 2):
            text, label = row['text'], row['label']
            if allowed.get(text) != label:
                raise ValueError(f'{split}:{line}: label differs from source template')
            key = ' '.join(text.casefold().split())
            if key in seen:
                raise ValueError(f'{split}:{line}: duplicate or overlapping review')
            seen.add(key)
            scripts[split] += bool(DEVANAGARI.search(text))

    generate = module['main']
    with tempfile.TemporaryDirectory() as tmp:
        generate.__globals__['ROOT'] = Path(tmp)
        generate()
        for split in data:
            if data[split] != read(Path(tmp) / f'{split}.csv'):
                raise ValueError(f'{split}: regenerated rows differ')
    within_test = 0
    for index, row in enumerate(data['test']):
        for previous in data['test'][:index]:
            if row['label'] == previous['label']:
                score = difflib.SequenceMatcher(None, row['text'].casefold(), previous['text'].casefold()).ratio()
                within_test += score >= .9
    if within_test:
        raise ValueError(f'{within_test} same-label test pairs have similarity >= 0.90')
    result = {'train_rows': len(data['train']), 'test_rows': len(data['test']),
              'train_labels': dict(Counter(row['label'] for row in data['train'])),
              'test_labels': dict(Counter(row['label'] for row in data['test'])),
              'train_reviews_with_devanagari': scripts['train'], 'test_reviews_with_devanagari': scripts['test'],
              'template_label_mismatches': 0, 'duplicate_or_overlapping_reviews': 0,
              'same_label_test_pairs_similarity_ge_0_9': within_test,
              'reproduced_from_generator': True}
    out = ROOT.parent / 'results' / 'datasets' / 'review-sentiment-audit.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
