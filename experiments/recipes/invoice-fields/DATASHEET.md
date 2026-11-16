# Invoice fields dataset

## Source

Fictional invoice examples created for Ekido issue #25. No customer invoices or external company records were used.

## How it was made

An AI coding assistant wrote twenty training layouts and five held-out test layouts. `experiments/recipes/generate_invoice_fields.py` combines each layout with ten deterministically constructed sets of fields. Each label contains the exact vendor, invoice number, ISO date, total and GSTIN-shaped value displayed in the corresponding text. Values, company-like names, and document numbers are artificial. No open model or external invoice corpus was used.

The layouts and synthetic values are repetitive; scores on this dataset must not be presented as evidence of performance on real invoices. Train and test use different layouts, though they share field formats and the same generation method.

## Licence

Created for the Ekido project and contributed under the repository's licence.

## PII check

All vendor names are artificial `Zevix Sample Supplier` labels; dates, amounts and document numbers are generated. No real people, real invoices, phone numbers, addresses or email addresses were used. GSTIN-shaped strings deliberately have an incorrect check digit so they cannot be valid GSTINs; they preserve the standard 15-character structure but are not valid tax identifiers. This choice prevents real GSTINs from appearing but means the dataset cannot assess GSTIN checksum validation. The repository's PII pattern scanner may flag the PAN-shaped substring even though all identifiers are synthetic.

## Label distribution

The training set has 200 examples and the held-out test set has 50. Each JSON label has the same five keys: `vendor`, `invoice_no`, `date`, `total` and `gstin`. This is a field-extraction dataset rather than a class-labelled dataset.

## Author

The templates, generator and labels were written by an AI coding assistant for Vaibhav Parmar's Ekido issue #25.
