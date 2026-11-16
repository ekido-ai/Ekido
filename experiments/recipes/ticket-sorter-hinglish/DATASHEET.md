# Ticket sorter Hinglish dataset

## Source

Synthetic customer-support messages prepared for Ekido issue #24. No real customer tickets are used. The supplied source files were generated for this project; they were provided together with a PDF datasheet.

## How it was made

The source datasheet describes hand-written English, Roman Hinglish and Devanagari Hindi sentence patterns combined with synthetic product names, colours, sizes, amounts, short order references, durations and city names. It identifies the generation script as `gen_dataset_v2.py` with seed 42; that script was not supplied with the files, so its generation process could not be independently reproduced.

The supplied train and test sets use distinct held-out patterns. During review, selected product and size combinations were corrected, and several similar test messages were rewritten to improve diversity. These edits were made by the AI assistant from the supplied data. The dataset remains synthetic and template-based: its scores should not be assumed to represent performance on real customer messages. Character-level dissimilarity does not prove freedom from semantic overlap or memorisation.

## Licence

The supplied datasheet states that the dataset was generated for Ekido and may be used, modified and redistributed within the project and its repositories. The edited messages are contributed under the repository's licence.

## PII check

The supplied datasheet states that the data is synthetic and contains no real customer information. The dataset validator scans for email, Indian phone, Aadhaar and PAN patterns; a pass is not proof that every value is fictional. Order references are short synthetic numbers; city names and prices are generic. Do not add real customer records to this dataset.

## Label distribution

Each of the five labels (`complaint`, `order`, `question`, `refund`, `other`) has 100 training examples and 20 test examples. The source datasheet describes a per-label training mix of 40 English, 35 Roman Hinglish and 25 Devanagari examples, and a test mix of 8 English, 7 Roman Hinglish and 5 Devanagari examples. Targeted edits preserve the labels and broadly preserve the script mix; automatic character counts are recorded in the results file.

## Author

Source data supplied by Vaibhav Parmar, as attributed in the supplied datasheet. Targeted text edits and validation were performed with an AI coding assistant.
