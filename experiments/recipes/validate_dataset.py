"""Checks one recipe dataset folder before it can be used for training or baselines.

    python -I experiments/recipes/validate_dataset.py experiments/recipes/<recipe>

A folder holds train.csv, test.csv and DATASHEET.md. The checks:
- the recipe is known, and both files have exactly its columns, with every cell filled in
- enough rows in each file
- labels from the allowed set
- no duplicate rows, and no test row that also appears in train (compared on the input column, ignoring case
  and spacing)
- the datasheet has every required section
- Hinglish recipes include at least some Devanagari.

Text that looks like personal data (emails, Indian phone numbers, Aadhaar or PAN numbers) is counted and printed
as a warning. Datasets must use made-up values; the datasheet's "PII check" section says how that was ensured.

Exit code 0 means it passed. Every problem is printed, so one run shows everything to fix.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

RECIPES = {
    "ticket-sorter-hinglish": {"columns": ["text", "label"], "input": "text", "train": 500, "test": 100,
                               "labels": {"complaint", "order", "question", "refund", "other"}, "hinglish": True},
    "invoice-fields": {"columns": ["text", "json"], "input": "text", "train": 200, "test": 50, "json": True},
    "product-descriptions": {"columns": ["attributes", "description"], "input": "attributes", "train": 300, "test": 60},
    "faq-bot-hinglish": {"columns": ["question", "answer"], "input": "question", "train": 300, "test": 60, "hinglish": True},
    "review-sentiment": {"columns": ["text", "label"], "input": "text", "train": 500, "test": 100,
                         "labels": {"positive", "negative", "neutral"}},
}
INVOICE_KEYS = {"vendor", "invoice_no", "date", "total", "gstin"}
DATASHEET_SECTIONS = ["Source", "How it was made", "Licence", "PII check", "Label distribution", "Author"]
PII_PATTERNS = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "phone": re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)"),
    "aadhaar": re.compile(r"(?<!\d)\d{4}\s?\d{4}\s?\d{4}(?!\d)"),
    "pan": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
}
DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def _norm(value: str) -> str:
    return " ".join(value.lower().split())


def _read(path: Path, spec: dict, errors: list[str]) -> list[dict]:
    if not path.is_file():
        errors.append(f"{path.name}: missing")
        return []
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != spec["columns"]:
                errors.append(f"{path.name}: columns must be exactly {spec['columns']}, found {reader.fieldnames}")
                return []
            rows = list(reader)
    except UnicodeDecodeError:
        errors.append(f"{path.name}: not UTF-8")
        return []
    for number, row in enumerate(rows, start=2):  # line 1 is the header
        for column in spec["columns"]:
            if not (row.get(column) or "").strip():
                errors.append(f"{path.name} line {number}: '{column}' is empty")
    return rows


def _check_rows(name: str, rows: list[dict], spec: dict, minimum: int, errors: list[str]) -> None:
    if len(rows) < minimum:
        errors.append(f"{name}: {len(rows)} rows, needs at least {minimum}")
    if "labels" in spec:
        bad = Counter(r["label"] for r in rows if r.get("label") not in spec["labels"])
        for label, count in bad.items():
            errors.append(f"{name}: label '{label}' is not one of {sorted(spec['labels'])} ({count} rows)")
    if spec.get("json"):
        import json

        for number, row in enumerate(rows, start=2):
            try:
                value = json.loads(row.get("json") or "")
                missing = INVOICE_KEYS - set(value) if isinstance(value, dict) else INVOICE_KEYS
            except json.JSONDecodeError:
                missing = {"(not valid JSON)"}
            if missing:
                errors.append(f"{name} line {number}: json is missing {sorted(missing)}")
    seen = Counter(_norm(r.get(spec["input"]) or "") for r in rows)
    duplicates = [text for text, count in seen.items() if count > 1 and text]
    if duplicates:
        errors.append(f"{name}: {len(duplicates)} duplicated inputs, e.g. {duplicates[0][:60]!r}")


def validate(folder: Path) -> tuple[list[str], list[str]]:
    """Returns (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []
    spec = RECIPES.get(folder.name)
    if spec is None:
        return [f"unknown recipe '{folder.name}'; the folder name must be one of {sorted(RECIPES)}"], warnings
    train = _read(folder / "train.csv", spec, errors)
    test = _read(folder / "test.csv", spec, errors)
    _check_rows("train.csv", train, spec, spec["train"], errors)
    _check_rows("test.csv", test, spec, spec["test"], errors)

    overlap = {_norm(r[spec["input"]]) for r in train} & {_norm(r[spec["input"]]) for r in test}
    overlap.discard("")
    if overlap:
        errors.append(f"{len(overlap)} test inputs also appear in train, e.g. {sorted(overlap)[0][:60]!r}")

    if spec.get("hinglish") and train + test:
        share = sum(bool(DEVANAGARI.search(" ".join(r.values()))) for r in train + test) / len(train + test)
        if share < 0.05:
            errors.append(f"Hinglish recipe: only {share:.0%} of rows contain Devanagari; include at least 5%")

    sheet = folder / "DATASHEET.md"
    if not sheet.is_file():
        errors.append("DATASHEET.md: missing")
    else:
        headings = {line.lstrip("#").strip().lower() for line in sheet.read_text(encoding="utf-8").splitlines() if line.startswith("#")}
        for section in DATASHEET_SECTIONS:
            if section.lower() not in headings:
                errors.append(f"DATASHEET.md: missing a '## {section}' section")

    hits = Counter()
    for row in train + test:
        text = " ".join(row.values())
        for kind, pattern in PII_PATTERNS.items():
            if pattern.search(text):
                hits[kind] += 1
    for kind, count in sorted(hits.items()):
        warnings.append(f"{count} rows contain something that looks like {kind}; make sure every value is made up")
    return errors, warnings


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    errors, warnings = validate(Path(argv[0]))
    for warning in warnings:
        print(f"warning: {warning}")
    for error in errors:
        print(f"error: {error}")
    print("PASS" if not errors else f"FAIL: {len(errors)} problems")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
