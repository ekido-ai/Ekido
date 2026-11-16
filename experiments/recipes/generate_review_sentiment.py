"""Generate templated synthetic product reviews with three sentiment labels."""
from __future__ import annotations

import csv
import difflib
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'review-sentiment'
PRODUCTS = ('backpack', 'water bottle', 'notebook', 'desk lamp', 't-shirt', 'mug',
            'bedsheet', 'running shoe', 'power bank', 'pillow', 'scarf', 'frying pan')

# Each group contains five English, six Roman Hinglish and four Devanagari patterns.
TRAIN = {
 'positive': (
  'I am very happy with the {product}.', 'I like the {product} and found it useful.',
  'Really pleased with the {product}; it meets my needs.', 'The {product} was a good purchase for me.',
  'I enjoyed using the {product} and would recommend it.',
  'Mujhe {product} bahut pasand aaya.', '{product} ka experience achha raha, main khush hoon.',
  '{product} meri zarurat ke liye sahi tha aur mujhe pasand hai.', 'Mere liye {product} lena sahi faisla tha.',
  '{product} se main santusht hoon, achha laga.', 'Main {product} se khush hoon, umeed par khara utara.',
  'मुझे {product} बहुत पसंद आया।', '{product} का अनुभव अच्छा रहा, मैं खुश हूँ।',
  '{product} लेकर मैं संतुष्ट हूँ।', 'यह {product} मेरी जरूरत के लिए अच्छा है।',
 ),
 'negative': (
  'I am very disappointed with the {product}.', 'The {product} did not meet my needs and I dislike it.',
  'I regret buying the {product}; it was a poor experience.', 'The {product} was a bad purchase for me.',
  'I disliked using the {product} and cannot recommend it.',
  'Mujhe {product} bilkul pasand nahi aaya.', '{product} ka experience kharab raha, main naraaz hoon.',
  '{product} meri zarurat ke liye sahi nahi tha aur mujhe pasand nahi hai.', 'Mere liye {product} lena galat faisla tha.',
  '{product} se main asantusht hoon, achha nahi laga.', 'Main {product} se niraash hoon, umeed par khara nahi utara.',
  'मुझे {product} बिल्कुल पसंद नहीं आया।', '{product} का अनुभव खराब रहा, मैं नाराज हूँ।',
  '{product} लेकर मैं असंतुष्ट हूँ।', 'यह {product} मेरी जरूरत के लिए अच्छा नहीं है।',
 ),
 'neutral': (
  'I received the {product} today.', 'The {product} arrived in a box.',
  'I have placed the {product} on the table.', 'The {product} was delivered this morning.',
  'I opened the package containing the {product}.',
  'Mujhe {product} aaj mila.', '{product} ek box mein aaya hai.',
  'Maine {product} table par rakha hai.', '{product} subah deliver hua tha.',
  'Maine {product} ka package khola.', '{product} mere paas ab aa gaya hai.',
  'मुझे {product} आज मिला।', '{product} एक डिब्बे में आया है।',
  'मैंने {product} मेज पर रखा है।', '{product} सुबह डिलीवर हुआ था।',
 ),
}
TEST = {
 'positive': (
  'The {product} has been a pleasant purchase and I am satisfied.',
  'I am pleased that the {product} suits what I needed.',
  '{product} khareedkar mujhe kaafi khushi hui.', 'Meri zarurat ke hisaab se {product} achha nikla, main khush hoon.',
  '{product} खरीदकर मुझे काफी खुशी हुई।', 'मेरी जरूरत के हिसाब से {product} अच्छा निकला, मैं खुश हूँ।',
 ),
 'negative': (
  'The {product} has been an unpleasant purchase and I am dissatisfied.',
  'I am unhappy that the {product} does not suit what I needed.',
  '{product} khareedkar mujhe kaafi niraasha hui.', 'Meri zarurat ke hisaab se {product} bura nikla, main dukhi hoon.',
  '{product} खरीदकर मुझे काफी निराशा हुई।', 'मेरी जरूरत के हिसाब से {product} खराब निकला, मैं दुखी हूँ।',
 ),
 'neutral': (
  'The parcel included one {product}.', 'I unpacked the {product} in the evening.',
  'Parcel ke andar ek {product} tha.', 'Shaam ko maine {product} unpack kiya.',
  'पार्सल के अंदर एक {product} था।', 'शाम को मैंने {product} पैकेट से निकाला।',
 ),
}


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20261116)
    result: dict[str, list[dict[str, str]]] = {'train': [], 'test': []}
    for label in ('positive', 'negative', 'neutral'):
        for split, patterns, amount in (('train', TRAIN[label], 166 if label == 'neutral' else 167),
                                         ('test', TEST[label], 34 if label == 'positive' else 33)):
            choices = [{'text': pattern.format(product=product), 'label': label}
                       for pattern in patterns for product in PRODUCTS]
            if split == 'train':
                selected = rng.sample(choices, amount)
            else:
                # Keep near-identical held-out reviews from inflating test coverage.
                rng.shuffle(choices)
                selected = []
                for candidate in choices:
                    text = candidate['text'].casefold()
                    if all(difflib.SequenceMatcher(None, text, prior['text'].casefold()).ratio() < 0.9
                           for prior in selected):
                        selected.append(candidate)
                        if len(selected) == amount:
                            break
                if len(selected) != amount:
                    raise ValueError(f'{label}: insufficient distinct test reviews')
            result[split].extend(selected)
    for split, items in result.items():
        rng.shuffle(items)
        with (ROOT / f'{split}.csv').open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=['text', 'label'])
            writer.writeheader()
            writer.writerows(items)
        print(f'{split}: {len(items)} examples')


if __name__ == '__main__':
    main()
