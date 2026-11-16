# Fictional clinic FAQ dataset

## Source

Fictional administrative FAQs created for Ekido issue #27. The sample clinic and all its policies are invented; they are not a source of information about any actual clinic. No real patient data, names, contact details or clinic records were used.

## How it was made

An AI coding assistant wrote 20 fictional administrative topics and corresponding answers in English, Roman Hinglish and Devanagari Hindi. `experiments/recipes/generate_clinic_faq.py` combines each topic with 15 training question templates and three held-out test templates. It uses six Roman, five English and four Devanagari templates per topic for training, plus one per language for testing.

The test questions have different wording but ask about the same 20 fictional facts as the training questions. This measures rephrasing of known FAQs, not generalisation to new clinics, new policies or medical questions. The examples are highly templated. They do not provide diagnosis, treatment, medication or emergency instructions and must not be used as real clinic guidance.

## Licence

Created for the Ekido project and contributed under the repository's licence.

## PII check

No real people, patient information, addresses, telephone numbers, email addresses or tax identifiers were used. The dataset validator also scans for several PII-shaped patterns; this is not a substitute for independent content review.

## Label distribution

This is a question-answering dataset rather than a class-labelled dataset. The training set has 300 examples: 100 English, 120 Roman Hinglish and 80 Devanagari. The test set has 60 examples: 20 per language. Across both splits, 140 of 360 questions use Roman Hinglish by the generation plan.

## Author

The fictional FAQ facts, multilingual answers, question templates and generator were written by an AI coding assistant for Vaibhav Parmar's Ekido issue #27.
