import csv
import difflib
import json
import re
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parent / 'ticket-sorter-hinglish'
def read(name):
    with (root / f'{name}.csv').open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))
train, test = read('train'), read('test')
norm = lambda s: ' '.join(s.casefold().split())
sim = difflib.SequenceMatcher()
closest = []
for row in test:
    a = norm(row['text'])
    best = 0.0
    sim.set_seq1(a)
    for other in train:
        sim.set_seq2(norm(other['text']))
        if sim.real_quick_ratio() > best and sim.quick_ratio() > best:
            best = max(best, sim.ratio())
    closest.append(best)
stats = {'method': 'casefold + whitespace normalization; difflib.SequenceMatcher ratio; all train/test pairs',
         'train_rows': len(train), 'test_rows': len(test),
         'train_labels': dict(Counter(r['label'] for r in train)),
         'test_labels': dict(Counter(r['label'] for r in test)),
         'train_devanagari_rows': sum(bool(re.search(r'[\u0900-\u097f]', r['text'])) for r in train),
         'test_devanagari_rows': sum(bool(re.search(r'[\u0900-\u097f]', r['text'])) for r in test),
         'train_test_exact_overlap': len({norm(r['text']) for r in train} & {norm(r['text']) for r in test}),
         'max_train_test_similarity': round(max(closest), 6),
         'test_rows_with_similarity_ge_0_8': sum(s >= .8 for s in closest)}
path = Path(__file__).resolve().parents[1] / 'results' / 'datasets' / 'ticket-sorter-hinglish-audit.json'
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(stats, indent=2) + '\n', encoding='utf-8')
print(json.dumps(stats, indent=2))
