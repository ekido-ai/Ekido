"""Builds the settlement Verdict. Every verifier must sign byte-identical data, or quorum can't form.

Verifier reports may differ slightly across devices, so a Verdict never commits to one report.
The flow has two phases: verifiers submit signed reports, the coordinator derives one Verdict from
them with these functions, then each verifier re-derives it, checks it, and signs it.
Hashes are SHA-256 over RFC 8785 canonical JSON. Standard library only.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping, Sequence

from .canonical import document_hash

USDC_BASE_UNITS = Decimal(1_000_000)
ZERO_BYTES32 = "0x" + "00" * 32


def to_bytes32(sha256_hex: str) -> str:
    if len(sha256_hex) != 64 or any(char not in "0123456789abcdefABCDEF" for char in sha256_hex):
        raise ValueError("expected a 64-character hex SHA-256")
    return "0x" + sha256_hex.lower()


def lineage_root(manifest_hashes: Sequence[str]) -> str:
    """Commits to the accepted chain, in order from root to tip. Order matters here."""
    if not manifest_hashes:
        raise ValueError("an accepted lineage can't be empty")
    return to_bytes32(document_hash({"kind": "gpuchain.lineage.v1", "manifests": list(manifest_hashes)}))


def quality_report_root(reports: Sequence[dict]) -> str:
    """Commits to the quorum's reports. Sorted and de-duplicated, so arrival order can't change the digest."""
    if not reports:
        raise ValueError("a verdict needs at least one quality report")
    hashes = sorted({document_hash(report) for report in reports})
    return to_bytes32(document_hash({"kind": "gpuchain.quality.v1", "reports": hashes}))


def to_base_units(amount: Decimal) -> int:
    """USDC has 6 decimals. Finer amounts are refused rather than silently rounded."""
    units = amount * USDC_BASE_UNITS
    if units != units.to_integral_value():
        raise ValueError(f"{amount} USDC has more than 6 decimal places")
    return int(units)


def build_verdict(
    *,
    onchain_job_id: str,
    passed: bool,
    final_checkpoint_hash: str | None,
    lineage: Sequence[str],
    reports: Sequence[dict],
    payouts: Mapping[str, Decimal],
    refund: Decimal,
    budget: Decimal,
    expiry: int,
    max_payees: int = 8,
) -> dict:
    """Same inputs give the same Verdict on every machine. Enforces what the contract will enforce."""
    if not passed and payouts:
        raise ValueError("a failed verdict pays no one: the client gets a full refund")
    if refund < 0 or any(amount < 0 for amount in payouts.values()):
        raise ValueError("payouts and the refund cannot be negative")
    positive = {address: amount for address, amount in payouts.items() if amount > 0}
    if len(positive) > max_payees:
        raise ValueError(f"{len(positive)} payees is over the limit of {max_payees}")
    # Sorted by numeric address, so payee order can't change the digest.
    payees = sorted(positive, key=lambda a: int(a, 16))
    amounts = [to_base_units(positive[address]) for address in payees]
    refund_units = to_base_units(refund)
    if sum(amounts) + refund_units != to_base_units(budget):
        raise ValueError("payouts plus refund must equal the budget exactly")
    return {
        "jobId": onchain_job_id,
        "passed": passed,
        "finalCheckpoint": to_bytes32(final_checkpoint_hash) if final_checkpoint_hash else ZERO_BYTES32,
        "lineageRoot": lineage_root(lineage) if lineage else ZERO_BYTES32,
        "qualityReport": quality_report_root(reports),
        "payees": payees,
        "amounts": amounts,
        "refund": refund_units,
        "expiry": expiry,
    }
