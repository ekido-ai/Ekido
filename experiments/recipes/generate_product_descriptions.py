"""Generate a small, fictional product-description example dataset."""
from __future__ import annotations

import csv
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'product-descriptions'
COLOURS = ('navy', 'green', 'red')
CATALOG = (
    ('t-shirt', 'cotton', ('S', 'M', 'L'), ('crew neck', 'short sleeves', 'ribbed collar', 'straight hem')),
    ('kurti', 'cotton', ('S', 'M', 'L'), ('round neck', 'three-quarter sleeves', 'side slits', 'straight hem')),
    ('water bottle', 'stainless steel', ('500 ml', '750 ml', '1 litre'), ('screw cap', 'carry loop', 'wide opening', 'matte finish')),
    ('mug', 'ceramic', ('200 ml', '300 ml', '400 ml'), ('curved handle', 'glossy finish', 'round base', 'straight sides')),
    ('notebook', 'paper', ('A5', 'A4', 'B5'), ('ruled pages', 'plain pages', 'grid pages', 'spiral binding')),
    ('cushion cover', 'cotton', ('30 x 30 cm', '40 x 40 cm', '45 x 45 cm'), ('zip closure', 'plain weave', 'envelope closure', 'printed front')),
    ('backpack', 'polyester', ('12 litres', '18 litres', '24 litres'), ('zip closure', 'side pocket', 'top handle', 'padded straps')),
    ('scarf', 'cotton', ('150 x 50 cm', '160 x 60 cm', '180 x 70 cm'), ('fringed ends', 'plain weave', 'striped pattern', 'stitched edges')),
    ('tote bag', 'canvas', ('small', 'medium', 'large'), ('long handles', 'zip closure', 'inside pocket', 'flat base')),
    ('pencil pouch', 'canvas', ('small', 'medium', 'large'), ('zip closure', 'flat base', 'wrist loop', 'inside divider')),
)

TRAIN_DESCRIPTIONS = (
    'This {colour} {material} {name} comes in size {size} and features {feature}.',
    'The {name} is made of {material}, is {colour}, and comes in size {size} with {feature}.',
    'Choose this {colour} {name} in {material}, size {size}, with {feature}.',
    'A {material} {name} in {colour}, size {size}, featuring {feature}.',
    'This {name} has a {colour} finish, {material} construction, size {size}, and {feature}.',
)
TEST_DESCRIPTIONS = (
    'In {colour}, this {material} {name} has {feature} and is available in size {size}.',
    'Size {size}: a {colour} {name} made from {material}, with {feature}.',
    'Made from {material}, the {colour} {name} is size {size} and includes {feature}.',
)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    rows: dict[str, list[dict[str, str]]] = {'train': [], 'test': []}
    for name, material, sizes, features in CATALOG:
        combinations = list(product(COLOURS, sizes, features))
        for index, (colour, size, feature) in enumerate(combinations):
            split = 'test' if index in {5, 11, 17, 23, 29, 35} else 'train'
            values = {'name': name, 'material': material, 'colour': colour, 'size': size, 'feature': feature}
            attributes = '; '.join(f'{key}: {value}' for key, value in values.items())
            templates = TEST_DESCRIPTIONS if split == 'test' else TRAIN_DESCRIPTIONS
            template_index = (index // 6) % len(templates) if split == 'test' else index % len(templates)
            rows[split].append({'attributes': attributes, 'description': templates[template_index].format(**values)})
    for split, items in rows.items():
        with (ROOT / f'{split}.csv').open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=['attributes', 'description'])
            writer.writeheader()
            writer.writerows(items)
        print(f'{split}: {len(items)} examples')


if __name__ == '__main__':
    main()
