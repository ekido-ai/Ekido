# Product descriptions dataset

## Source

Fictional product specifications and descriptions created for Ekido issue #26. No external listings, real companies, customer data or product catalogues were used.

## How it was made

An AI coding assistant wrote a small synthetic catalogue of ten product categories, each with an explicit material, sizes and features, and wrote description templates. `experiments/recipes/generate_product_descriptions.py` enumerates 36 combinations per category, assigning 30 to training and 6 to the held-out test split. The test split uses distinct attribute combinations and its own description templates. Inputs include product name, material, colour, size and feature; outputs describe those supplied values.

The dataset is highly templated and the split shares a small vocabulary of products, attributes and generation rules. It is useful as a reproducible example, not as evidence of generalisation to real product catalogues or arbitrary writing styles. ROUGE-L may reward surface similarity rather than factual quality.

## Licence

Created for the Ekido project and contributed under the repository's licence.

## PII check

The examples contain synthetic product attributes and no customer information, personal names, addresses, phone numbers, email addresses or tax identifiers. The dataset validator checks for several PII-shaped patterns; this does not replace an independent content review.

## Label distribution

This is a generation dataset rather than a class-labelled dataset. The 300 training and 60 test rows are balanced by the ten product categories: 30 training and 6 test examples per category.

## Author

The catalogue, templates and generator were written by an AI coding assistant for Vaibhav Parmar's Ekido issue #26.
