"""The protocol fee: a share of accepted work, paid by the client on top of the providers' prices.

The fee is part of the job spec, so its rate and recipient are inside the spec hash the escrow stores when the
client funds the job. Verifiers recompute it from that spec independently; the coordinator can't raise it later.

Rules, the same everywhere (coordinator, verifiers, dashboard):
- Providers are paid first, but only up to budget × 10000 / (10000 + bps), so the fee always fits.
- fee = providers' total × bps / 10000, rounded down to whole micro-USDC.
- No fee on a failed job: it refunds in full.
- Whatever is left goes back to the client.
"""
from __future__ import annotations

import re
from decimal import ROUND_DOWN, Decimal
from typing import Mapping

FEE_KEY = "protocol_fee"
MAX_FEE_BPS = 2000
MICRO = Decimal("0.000001")


def fee_terms(spec: Mapping) -> tuple[int, str] | None:
    """(bps, recipient) when the spec carries a fee, else None. Assumes fee_problems found nothing."""
    fee = spec.get(FEE_KEY)
    if not fee:
        return None
    return int(fee["bps"]), str(fee["recipient"]).lower()


def fee_problems(spec: Mapping) -> list[str]:
    fee = spec.get(FEE_KEY)
    if fee is None:
        return []
    if not isinstance(fee, dict) or set(fee) != {"bps", "recipient"}:
        return [f"{FEE_KEY} must have exactly bps and recipient"]
    problems = []
    if type(fee["bps"]) is not int or not 0 <= fee["bps"] <= MAX_FEE_BPS:
        problems.append(f"{FEE_KEY}.bps must be a whole number from 0 to {MAX_FEE_BPS}")
    if not isinstance(fee["recipient"], str) or not re.fullmatch(r"0x[0-9a-fA-F]{40}", fee["recipient"]) or int(fee["recipient"], 16) == 0:
        problems.append(f"{FEE_KEY}.recipient must be a non-zero address")
    return problems


def provider_budget(budget: Decimal, bps: int) -> Decimal:
    """The most the providers can be paid so that their total plus the fee stays within the budget."""
    return (budget * 10_000 / (10_000 + bps)).quantize(MICRO, rounding=ROUND_DOWN)


def fee_amount(provider_total: Decimal, bps: int) -> Decimal:
    return (provider_total * bps / 10_000).quantize(MICRO, rounding=ROUND_DOWN)


def add_fee(payouts: Mapping[str, Decimal], budget: Decimal, terms: tuple[int, str] | None) -> tuple[dict[str, Decimal], Decimal]:
    """Provider payouts by wallet, plus the fee as one more payee. Returns (payouts, refund)."""
    merged = {wallet.lower(): amount for wallet, amount in payouts.items()}
    total = sum(merged.values(), Decimal(0))
    fee = Decimal(0)
    if terms is not None and total > 0:
        bps, recipient = terms[0], terms[1].lower()
        fee = fee_amount(total, bps)
        if fee > 0:
            merged[recipient] = merged.get(recipient, Decimal(0)) + fee
    refund = budget - total - fee
    if refund < 0:
        raise ValueError("payouts and fee exceed the budget")
    return merged, refund
