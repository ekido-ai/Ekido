"""The five ready-made recipes: how a dataset row becomes a training example, and how a model's answers are scored.

Shared by the coordinator (quotes, validation), the training runtime and the verifiers, so all three agree on the
prompt format and the metric. Dependency-free on purpose.

Quality is judged per test example: each one passes or fails under its recipe's rule, and the floor is the share
that must pass. Keeping every recipe to pass/fail lets one statistical check (ekido_core.quality) serve all of them.

The floors here are starting points. They are replaced by measured baselines (ticket V2: the base model's score with
a prompt, no training) before a customer sees them, and every quote states its floor in plain words.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Recipe:
    recipe_id: str
    title: str
    task: str  # classification, extraction, generation or qa
    columns: tuple[str, str]  # (input column, target column)
    instruction: str
    input_name: str
    answer_name: str
    metric: str  # accuracy, field_f1 or rouge_l
    floor: float  # The share of test examples that must pass.
    labels: tuple[str, ...] = ()
    max_answer_tokens: int = 16
    pass_score: float = 1.0  # An example passes when its score reaches this: 1.0 means fully correct.

    def prompt(self, value: str) -> str:
        return f"{self.instruction}\n{self.input_name}: {value.strip()}\n{self.answer_name}:"

    def example(self, row: dict) -> dict:
        """A training example: the prompt, and the completion the model learns to write after it."""
        source, target = self.columns
        return {"prompt": self.prompt(row[source]), "completion": " " + row[target].strip()}

    def plain_words(self, test_rows: int) -> str:
        if self.metric == "accuracy":
            return f"At least {self.floor:.0%} of your {test_rows} test examples answered correctly"
        if self.metric == "field_f1":
            return f"At least {self.floor:.0%} of your {test_rows} test documents read with every field correct"
        return f"At least {self.floor:.0%} of the answers close to your {test_rows} reference answers"


RECIPES: dict[str, Recipe] = {
    r.recipe_id: r
    for r in (
        Recipe(
            "ticket-sorter-hinglish", "Sort support tickets (Hinglish)", "classification", ("text", "label"),
            "Sort this customer support ticket into exactly one category: complaint, order, question, refund or other.",
            "Ticket", "Category", "accuracy", 0.80, ("complaint", "order", "question", "refund", "other"), 4,
        ),
        Recipe(
            "invoice-fields", "Read invoices", "extraction", ("text", "json"),
            "Extract vendor, invoice_no, date, total and gstin from this invoice as JSON.",
            "Invoice", "JSON", "field_f1", 0.70, (), 128,
        ),
        Recipe(
            "product-descriptions", "Write product descriptions", "generation", ("attributes", "description"),
            "Write a short, friendly product description from these details.",
            "Product", "Description", "rouge_l", 0.60, (), 128, 0.4,
        ),
        Recipe(
            "faq-bot-hinglish", "Answer customer questions (Hinglish)", "qa", ("question", "answer"),
            "Answer the customer's question for the clinic, in the language they used.",
            "Question", "Answer", "rouge_l", 0.60, (), 160, 0.4,
        ),
        Recipe(
            "review-sentiment", "Review sentiment", "classification", ("text", "label"),
            "Is this review positive, negative or neutral? Answer with one word.",
            "Review", "Sentiment", "accuracy", 0.80, ("positive", "negative", "neutral"), 4,
        ),
    )
}
INVOICE_FIELDS = ("vendor", "invoice_no", "date", "total", "gstin")


def recipe(recipe_id: str) -> Recipe:
    try:
        return RECIPES[recipe_id]
    except KeyError:
        raise ValueError(f"unknown recipe {recipe_id!r}; choose one of {', '.join(sorted(RECIPES))}") from None


def _norm(text: str) -> str:
    return " ".join(str(text).lower().split())


def _first_label(answer: str, labels: tuple[str, ...]) -> str:
    """The first allowed label in a generated answer, so "Refund hai ye" counts as refund."""
    words = re.findall(r"[a-z]+", answer.lower())
    return next((w for w in words if w in labels), "")


def _fields(text: str) -> dict:
    match = re.search(r"\{.*\}", text, flags=re.S)
    try:
        value = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _lcs(a: list[str], b: list[str]) -> int:
    previous = [0] * (len(b) + 1)
    for x in a:
        current = [0]
        for j, y in enumerate(b):
            current.append(previous[j] + 1 if x == y else max(previous[j + 1], current[j]))
        previous = current
    return previous[-1]


def rouge_l(prediction: str, reference: str) -> float:
    p, r = _norm(prediction).split(), _norm(reference).split()
    if not p or not r:
        return 0.0
    common = _lcs(p, r)
    if common == 0:
        return 0.0
    precision, recall = common / len(p), common / len(r)
    return 2 * precision * recall / (precision + recall)


def score_one(recipe_id: str, prediction: str, reference: str) -> float:
    """One example's score in [0, 1], under the recipe's metric."""
    r = recipe(recipe_id)
    if r.metric == "accuracy":
        return 1.0 if _first_label(prediction, r.labels) == _norm(reference) else 0.0
    if r.metric == "field_f1":
        got, want = _fields(prediction), _fields(reference)
        hits = sum(1 for f in INVOICE_FIELDS if f in want and _norm(got.get(f, "")) == _norm(want[f]))
        return hits / max(1, sum(1 for f in INVOICE_FIELDS if f in want))
    return rouge_l(prediction, reference)


def passes(recipe_id: str, prediction: str, reference: str) -> bool:
    """Whether one example counts as correct: its score reaches the recipe's pass mark."""
    return score_one(recipe_id, prediction, reference) >= recipe(recipe_id).pass_score


def score(recipe_id: str, predictions: list[str], references: list[str]) -> float:
    """The mean score over a test set. Reported next to the pass rate, which is what the floor is compared with."""
    if len(predictions) != len(references) or not references:
        raise ValueError("need one prediction per reference, and at least one reference")
    return sum(score_one(recipe_id, p, r) for p, r in zip(predictions, references)) / len(references)


def eval_set_hash(recipe_id: str, test_rows: list[dict]) -> str:
    """Fingerprint of a test set, fixed in the quality policy before training so it can't be swapped later."""
    import hashlib

    source, target = recipe(recipe_id).columns
    digest = hashlib.sha256(recipe_id.encode())
    for row in test_rows:
        digest.update(json.dumps([row[source], row[target]], ensure_ascii=False, separators=(",", ":")).encode())
    return digest.hexdigest()
