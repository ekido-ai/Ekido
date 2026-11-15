"""Checks the labelled PII test set used to measure in-browser PII stripping.

    python -I experiments/pii/validate_pii_set.py [path/to/pii-set.jsonl]

Each line is {"text": str, "spans": [{"start": int, "end": int, "type": str}]}. The checks:
- at least 300 lines, each valid JSON with those keys
- every span lies inside its text, is non-empty, has a known type, and doesn't overlap another span on that line
- at least 60 lines with no spans, so false positives can be measured
- every type appears at least 10 times
- AADHAAR spans are 12 digits that pass the Verhoeff check, PAN spans look like ABCDE1234F, and EMAIL spans
  contain an @ (so labels match what they claim to be)
- no duplicate texts, and DATASHEET.md exists next to the set.

Exit code 0 means it passed. Every problem is printed.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

TYPES = {"NAME", "PHONE", "EMAIL", "AADHAAR", "PAN", "GSTIN", "UPI_ID", "ADDRESS"}
MIN_LINES, MIN_CLEAN, MIN_PER_TYPE = 300, 60, 10
PAN = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$")

# Verhoeff tables (the checksum Aadhaar numbers use).
_D = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
      [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
      [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
      [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]]
_P = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
      [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
      [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]]


def verhoeff_ok(digits: str) -> bool:
    check = 0
    for position, digit in enumerate(reversed(digits)):
        check = _D[check][_P[position % 8][int(digit)]]
    return check == 0


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"{path}: missing"]
    if not (path.parent / "DATASHEET.md").is_file():
        errors.append("DATASHEET.md: missing next to the set")
    lines = path.read_text(encoding="utf-8").splitlines()
    records = []
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {number}: not valid JSON ({exc.msg})")
            continue
        text, spans = record.get("text") if isinstance(record, dict) else None, record.get("spans") if isinstance(record, dict) else None
        if not isinstance(text, str) or not text.strip() or not isinstance(spans, list):
            errors.append(f"line {number}: needs a non-empty 'text' and a 'spans' list")
            continue
        records.append((number, text, spans))

    if len(records) < MIN_LINES:
        errors.append(f"{len(records)} lines, needs at least {MIN_LINES}")
    clean = sum(1 for _, _, spans in records if not spans)
    if clean < MIN_CLEAN:
        errors.append(f"{clean} lines with no PII, needs at least {MIN_CLEAN}")
    duplicates = [t for t, c in Counter(" ".join(t.lower().split()) for _, t, _ in records).items() if c > 1]
    if duplicates:
        errors.append(f"{len(duplicates)} duplicated texts, e.g. {duplicates[0][:60]!r}")

    per_type = Counter()
    for number, text, spans in records:
        taken: list[tuple[int, int]] = []
        for span in spans:
            start, end, kind = (span.get(k) for k in ("start", "end", "type")) if isinstance(span, dict) else (None, None, None)
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
                errors.append(f"line {number}: span {span} is outside the text (length {len(text)})")
                continue
            if kind not in TYPES:
                errors.append(f"line {number}: type {kind!r} is not one of {sorted(TYPES)}")
                continue
            if any(start < e and s < end for s, e in taken):
                errors.append(f"line {number}: span {start}-{end} overlaps another span")
            taken.append((start, end))
            per_type[kind] += 1
            value = text[start:end]
            if kind == "AADHAAR":
                digits = re.sub(r"[\s-]", "", value)
                if not (len(digits) == 12 and digits.isdigit() and digits[0] not in "01" and verhoeff_ok(digits)):
                    errors.append(f"line {number}: AADHAAR span {value!r} isn't 12 digits passing the Verhoeff check")
            elif kind == "PAN" and not PAN.match(value):
                errors.append(f"line {number}: PAN span {value!r} doesn't look like ABCDE1234F")
            elif kind == "EMAIL" and "@" not in value:
                errors.append(f"line {number}: EMAIL span {value!r} has no @")
    for kind in sorted(TYPES):
        if per_type[kind] < MIN_PER_TYPE:
            errors.append(f"type {kind} appears {per_type[kind]} times, needs at least {MIN_PER_TYPE}")
    return errors


def main(argv: list[str]) -> int:
    path = Path(argv[0]) if argv else Path(__file__).resolve().parent / "pii-set.jsonl"
    errors = validate(path)
    for error in errors:
        print(f"error: {error}")
    print("PASS" if not errors else f"FAIL: {len(errors)} problems")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
