"""Audit product attributes, outputs, split separation and reproducibility."""
from __future__ import annotations

import csv
import json
import runpy
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'product-descriptions'
FIELDS = {'name', 'material', 'colour', 'size', 'feature'}


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    data = {split: read(DATA / f'{split}.csv') for split in ('train', 'test')}
    seen: set[str] = set()
    categories: dict[str, Counter[str]] = {}
    for split, rows in data.items():
        expected = 300 if split == 'train' else 60
        if len(rows) != expected:
            raise ValueError(f'{split}: expected {expected} rows, got {len(rows)}')
        categories[split] = Counter()
        for line, row in enumerate(rows, 2):
            parts = dict(piece.split(': ', 1) for piece in row['attributes'].split('; '))
            if set(parts) != FIELDS or not all(parts.values()):
                raise ValueError(f'{split}:{line}: invalid attributes')
            if not all(value.casefold() in row['description'].casefold() for value in parts.values()):
                raise ValueError(f'{split}:{line}: description omits an attribute')
            if f"size {parts['size']}".casefold() not in row['description'].casefold():
                raise ValueError(f'{split}:{line}: description omits size')
            key = ' '.join(row['attributes'].casefold().split())
            if key in seen:
                raise ValueError(f'{split}:{line}: duplicate or overlapping attributes')
            seen.add(key)
            categories[split][parts['name']] += 1
        if set(categories[split].values()) != {expected // 10}:
            raise ValueError(f'{split}: product categories are not balanced')

    module = runpy.run_path(str(ROOT / 'generate_product_descriptions.py'))
    generate = module['main']
    with tempfile.TemporaryDirectory() as tmp:
        generate.__globals__['ROOT'] = Path(tmp)
        generate()
        for split in data:
            if data[split] != read(Path(tmp) / f'{split}.csv'):
                raise ValueError(f'{split}: regenerated rows differ')

    result = {'train_rows': len(data['train']), 'test_rows': len(data['test']),
              'train_by_product': dict(categories['train']), 'test_by_product': dict(categories['test']),
              'missing_attribute_values_in_descriptions': 0, 'duplicate_or_overlapping_attributes': 0,
              'reproduced_from_generator': True}
    out = ROOT.parent / 'results' / 'datasets' / 'product-descriptions-audit.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
