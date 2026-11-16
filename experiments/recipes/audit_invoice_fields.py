"""Verify synthetic field labels, split separation and deliberately invalid GSTIN checksums."""
from __future__ import annotations

import csv
import json
import re
import runpy
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'invoice-fields'
ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
KEYS = {'vendor', 'invoice_no', 'date', 'total', 'gstin'}
GSTIN = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$')


def valid_check_digit(gstin: str) -> str:
    total = 0
    for index, char in enumerate(gstin[:14]):
        value = ALPHABET.index(char) * (1 if index % 2 == 0 else 2)
        total += value // 36 + value % 36
    return ALPHABET[-total % 36]


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle))
    # Git may check out CSV files with CRLF, including line breaks within a
    # quoted invoice. Compare the same invoice content consistently on Windows
    # and Unix without changing any fields or labels.
    for row in rows:
        row['text'] = row['text'].replace('\r\n', '\n').replace('\r', '\n')
    return rows


def main() -> None:
    data = {split: read(DATA / f'{split}.csv') for split in ('train', 'test')}
    counts = {}
    seen_inputs: set[str] = set()
    for split, rows in data.items():
        expected_count = 200 if split == 'train' else 50
        if len(rows) != expected_count:
            raise ValueError(f'{split}: expected {expected_count}, found {len(rows)}')
        for index, row in enumerate(rows, 2):
            values = json.loads(row['json'])
            if set(values) != KEYS or not all(isinstance(v, str) and v for v in values.values()):
                raise ValueError(f'{split}:{index}: invalid fields')
            if not all(value in row['text'] for value in values.values()):
                raise ValueError(f'{split}:{index}: a label value is missing from the invoice')
            date.fromisoformat(values['date'])
            if not re.fullmatch(r'\d+\.\d{2}', values['total']):
                raise ValueError(f'{split}:{index}: invalid total')
            gstin = values['gstin']
            if not GSTIN.fullmatch(gstin) or gstin[-1] == valid_check_digit(gstin):
                raise ValueError(f'{split}:{index}: GSTIN must have the expected shape and an invalid check digit')
            normalized = ' '.join(row['text'].casefold().split())
            if normalized in seen_inputs:
                raise ValueError(f'{split}:{index}: duplicated or overlapping invoice')
            seen_inputs.add(normalized)
        counts[split] = len(rows)

    # Confirm the checked-in CSV rows can be reconstructed from the source templates.
    module = runpy.run_path(str(ROOT / 'generate_invoice_fields.py'))
    generate = module['main']
    with tempfile.TemporaryDirectory() as tmp:
        generate.__globals__['ROOT'] = Path(tmp)
        generate()
        for split in data:
            if data[split] != read(Path(tmp) / f'{split}.csv'):
                raise ValueError(f'{split}: generated rows differ from checked-in data')

    result = {'train_rows': counts['train'], 'test_rows': counts['test'], 'label_fields': sorted(KEYS),
              'text_label_mismatches': 0, 'duplicate_or_overlapping_inputs': 0,
              'structurally_valid_deliberately_bad_checksum_ids': sum(counts.values()),
              'reproduced_from_generator': True}
    out = ROOT.parent / 'results' / 'datasets' / 'invoice-fields-audit.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
