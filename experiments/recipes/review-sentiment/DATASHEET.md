# Review sentiment dataset

## Source

Fictional product reviews created for Ekido issue #28. No real customer reviews, personal information, company names or external review corpus were used.

## How it was made

An AI coding assistant wrote positive, negative and neutral sentence patterns in English, Roman Hinglish and Devanagari Hindi. `experiments/recipes/generate_review_sentiment.py` fills those patterns with 12 generic product names, selects rows using seed `20261116` and uses separate patterns for the held-out test split. Within each test label, it rejects pairs with a case-insensitive `difflib.SequenceMatcher` ratio of 0.90 or higher. This character-level filter does not guarantee semantic diversity.

The data is highly templated, with repeated wording and product names. Negative examples mostly express explicit dissatisfaction and neutral examples describe events without an opinion. Mixed or ambiguous sentiment and longer reviews are not represented well. The held-out examples use different phrases but share the product vocabulary and generation method, so this dataset cannot establish performance on real customer reviews.

## Licence

Created for the Ekido project and contributed under the repository's licence.

## PII check

Examples contain fictional, generic product reviews. They were created without real names, customer records, addresses, phone numbers, emails or tax identifiers. The dataset validator scans for several PII-shaped patterns; this does not replace independent content review.

## Label distribution

Training has 167 positive, 167 negative and 166 neutral examples. Testing has 34 positive, 33 negative and 33 neutral examples. This is nearly balanced; exact counts and Devanagari character counts are recorded in the audit results.

## Author

The fictional review templates and generator were written by an AI coding assistant for Vaibhav Parmar's Ekido issue #28.
