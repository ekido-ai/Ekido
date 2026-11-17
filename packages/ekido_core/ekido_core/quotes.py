"""Quotes in rupees: what a training job costs, before the customer pays.

Money is whole paise (integers) everywhere, so nothing is lost to rounding. A quote is a plain dictionary whose
SHA-256 (`terms_hash`) is stored with the job: the price, the plan and the quality terms a customer agreed to can't
be changed afterwards without the hash changing.

How a price is built:
    training tokens = training rows x fixed example length x epochs     (examples are padded to one length)
    compute         = tokens x the base model's price per million tokens, with a minimum per job
    distillation    = generated examples x a price each                 (only when the customer asks for it)
    taxable         = compute + distillation                            (Ekido's fee is a share of this, not added on)
    GST             = 18% of taxable, rounded to the nearest paisa
    total           = taxable + GST

PRICES ARE PROVISIONAL. The numbers in DEFAULT_PRICES are placeholders so the flow can be built and tested. They
must be replaced by prices set from measured costs on real hardware before any customer sees a quote.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .canonical import document_hash
from .job_spec import LLM_BASES
from .recipes import recipe

GST_BPS = 1800  # 18% GST on software services.
QUOTE_VALID_FOR = timedelta(minutes=30)
EPOCHS = 3
LOGICAL_BATCH_SIZE = 16
MAX_SEQ_LENGTH = {"classification": 256, "extraction": 768, "generation": 512, "qa": 512}
DISTILL_TARGET_ROWS = 1000  # Training examples the teacher model writes when the customer has only a few.


@dataclass(frozen=True)
class PriceList:
    """Provisional placeholders (see the module docstring). All amounts in paise."""

    per_million_tokens: dict = field(default_factory=lambda: {LLM_BASES[0]: 4_000, LLM_BASES[1]: 9_000})
    minimum_job: int = 9_900
    per_distilled_row: int = 5
    hosting_per_1000_requests: dict = field(default_factory=lambda: {LLM_BASES[0]: 200, LLM_BASES[1]: 500})
    fee_bps: int = 1000  # Ekido's share of the taxable amount; the rest is the providers' budget.
    tokens_per_second: dict = field(default_factory=lambda: {LLM_BASES[0]: 6_000, LLM_BASES[1]: 2_500})  # For the time estimate only.


DEFAULT_PRICES = PriceList()


class QuoteError(ValueError):
    pass


def gst(taxable_paise: int) -> int:
    """18% of the taxable amount, rounded half up to a whole paisa."""
    return (taxable_paise * GST_BPS + 5_000) // 10_000


def training_plan(recipe_id: str, train_rows: int, distill: bool = False) -> dict:
    """The training run a quote pays for: how many examples, how long each is, and how many steps."""
    if type(train_rows) is not int or train_rows < 1:
        raise QuoteError("train_rows must be a whole number of at least 1")
    rows = max(train_rows, DISTILL_TARGET_ROWS) if distill else train_rows
    steps = math.ceil(rows * EPOCHS / LOGICAL_BATCH_SIZE)
    return {
        "train_rows": rows,
        "generated_rows": rows - train_rows,
        "epochs": EPOCHS,
        "logical_batch_size": LOGICAL_BATCH_SIZE,
        "max_seq_length": MAX_SEQ_LENGTH[recipe(recipe_id).task],
        "total_logical_steps": steps,
    }


def make_quote(*, recipe_id: str, base_model: str, train_rows: int, test_rows: int, dataset_sha256: str, distill: bool = False,
               hosting_requests_per_month: int = 0, prices: PriceList = DEFAULT_PRICES, now: datetime | None = None) -> dict:
    """A quote for one job. Raises QuoteError with a message a customer can act on."""
    r = recipe(recipe_id)
    if base_model not in LLM_BASES:
        raise QuoteError(f"base_model must be one of {', '.join(LLM_BASES)}")
    if type(test_rows) is not int or test_rows < 20:
        raise QuoteError("a job needs at least 20 test examples, so the quality check means something")
    if type(hosting_requests_per_month) is not int or hosting_requests_per_month < 0:
        raise QuoteError("hosting_requests_per_month must be a whole number, 0 or more")
    now = now or datetime.now(timezone.utc)
    plan = training_plan(recipe_id, train_rows, distill)

    tokens = plan["train_rows"] * plan["max_seq_length"] * plan["epochs"]
    compute = max(prices.minimum_job, math.ceil(tokens * prices.per_million_tokens[base_model] / 1_000_000))
    distillation = plan["generated_rows"] * prices.per_distilled_row
    taxable = compute + distillation
    tax = gst(taxable)
    fee = taxable * prices.fee_bps // 10_000
    quote = {
        "schema_version": 1,
        "currency": "INR",
        "recipe_id": recipe_id,
        "base_model": base_model,
        "dataset_sha256": dataset_sha256,
        "test_rows": test_rows,
        "distill": bool(distill),
        "plan": plan,
        "compute_paise": compute,
        "distillation_paise": distillation,
        "training_paise": taxable,
        "gst_paise": tax,
        "total_paise": taxable + tax,
        "ekido_fee_paise": fee,
        "provider_budget_paise": taxable - fee,
        "hosting_paise_per_1000": prices.hosting_per_1000_requests[base_model],
        "hosting_requests_per_month": hosting_requests_per_month,
        "eta_minutes": max(5, math.ceil(tokens / prices.tokens_per_second[base_model] / 60) + 5),
        "quality_terms": {"metric": r.metric, "floor": r.floor,
                          "plain_words": r.plain_words(test_rows) + "; the model must also perform better than the untrained base on the same examples"},
        "refund_policy": "Full refund if the model misses the quality floor or does not beat the untrained base on your test examples.",
        "prices_provisional": True,
        "created_at": now.isoformat(timespec="seconds"),
        "expires_at": (now + QUOTE_VALID_FOR).isoformat(timespec="seconds"),
    }
    quote["terms_hash"] = document_hash(quote)
    return quote


def verify_quote(quote: dict, now: datetime | None = None) -> None:
    """Refuses a quote that was altered or has expired. Called before taking payment and before starting the job."""
    body = {k: v for k, v in quote.items() if k != "terms_hash"}
    if document_hash(body) != quote.get("terms_hash"):
        raise QuoteError("this quote was changed after it was issued")
    if (now or datetime.now(timezone.utc)) >= datetime.fromisoformat(quote["expires_at"]):
        raise QuoteError("this quote has expired; ask for a new one")


def rupees(paise: int) -> str:
    """Paise as a display string with Indian digit grouping: 12345678 -> '₹1,23,456.78'."""
    whole, part = divmod(abs(paise), 100)
    digits = str(whole)
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return f"{'-' if paise < 0 else ''}₹{','.join(groups + [tail])}.{part:02d}"
