# PII test set

`pii-set.jsonl` is the labelled set used to measure Ekido's in-browser personal-data stripping (recall and precision per type). It is scored by `experiments/pii/score.py` (ticket A6).

## Source

Fully synthetic. Written for Ekido issue ekido-ai/ekido-internal#36 (A2). No real customer, employee or provider data was used, and none must ever be added.

## How it was made

`generate_pii_set.py` builds every line from hand-written sentence patterns (English, Roman Hinglish and Devanagari Hindi) by filling slots with made-up values, with a fixed seed (`20261117`). Running it again writes an identical file. Span offsets are computed while the text is built, so they always match the text.

| Value | How it is made up |
|---|---|
| NAME | A random first name plus surname from two short lists of common Indian names (Roman and Devanagari pairs) |
| PHONE | 10 random digits starting 6 to 9, written plain, as `+91...`, as `+91 xxxxx xxxxx` or as `xxxxx-xxxxx`. Random digits can coincide with a real number; nobody is meant by any of them |
| EMAIL | `firstname.lastname` style local part at the reserved domains `example.com`, `example.org`, `example.net` |
| AADHAAR | 12 random digits, first digit 2 to 9, last digit chosen so the Verhoeff check passes; written plain, with spaces or with hyphens |
| PAN | `AAAPA1234A` format: three letters, `P`, a letter, four digits, a letter. Random, not checked against any register |
| GSTIN | 2-digit state code, a random PAN, an entity digit, `Z` and a correct check character |
| UPI_ID | a made-up handle (`name`, `name12`, or a 10-digit number) at a real bank handle such as `okaxis` or `ybl`. Random, not checked against any bank |
| ADDRESS | house number, a generic locality name, a city and its main pincode. House numbers are random, so the addresses do not point at real homes |

Span convention: a span covers only the value. It leaves out trailing punctuation and the words around it ("PAN", "Aadhaar", "ph"). An address span runs from the house or flat word to the end of the pincode.

## Contents (measured on the committed file)

- 300 lines: 240 with at least one PII span, **60 with no PII at all**.
- 438 spans in total: NAME 101, PHONE 73, EMAIL 69, ADDRESS 47, PAN 44, GSTIN 41, UPI_ID 32, AADHAAR 31.
- 129 lines carry more than one span.
- Language mix by pattern: about 45% English, 40% Roman Hinglish, 15% Devanagari (45 lines contain Devanagari).
- Phone, Aadhaar and email values in Devanagari lines are written with ASCII digits and letters. Devanagari digits are not covered.

### The 60 lines with no PII

They measure false positives, and many are deliberately tricky:
- order numbers and invoice numbers (`ORD123456`, `INV-2026-12345`);
- 12 lines with a 10-digit tracking number that starts with 6 to 9 and so looks like a phone number;
- 6 lines with a 12-digit courier reference that fails the Verhoeff check, so it looks like an Aadhaar number but is not one;
- 6 lines with a coupon code shaped like a PAN (five letters, four digits, a letter);
- prices, quantities, product and city names.

A detector that flags these has a false positive; one that ignores a real Aadhaar written with hyphens has a miss.

## Known limits

- Template-based: scores on this set will be higher than on real, messy customer text. Quote them as "on Ekido's synthetic test set", never as general accuracy.
- Only these 8 types. Bank account numbers, passport and driving-licence numbers, dates of birth and card numbers are not labelled.
- Names are common first-name and surname pairs; unusual names, single names and names that are also ordinary words are missing.
- Do not tune a detector by reading this set and then quote its score on the same set. Keep a second, unseen set for that.

## Licence and author

Contributed under the repository's licence. Written by Arvind (GitHub: arvindkushwaha55) with an AI coding assistant; the generator script is the source of record.

## How to check

```
python -I experiments/pii/validate_pii_set.py
python -I experiments/pii/generate_pii_set.py --out some/other/path.jsonl   # reproduces the same file
```
