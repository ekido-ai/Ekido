"""A provider's public terms, committed on-chain in ProviderRegistry.

The provider's own wallet registers keccak256(canonical JSON of these terms). Anyone can then recompute
the hash from what the coordinator publishes and see whether the coordinator shows the provider's name and
price exactly as the provider committed them, or hides the provider altogether.

The dashboard recomputes the same bytes in TypeScript (apps/web-combined/src/lib/chain/registry.ts); the
vector in tests/test_provider_meta.py pins both.
"""
from __future__ import annotations

import re
from decimal import Decimal

from eth_utils import keccak

from .canonical import canonical_bytes

META_KIND = "gpuchain.provider_meta.v1"

#: ProviderRegistry deployments. Public addresses only.
REGISTRIES = {84532: "0xcdf927CE0D885552529C5463993e64429a51c2Ff"}


def price_micros(price: str | Decimal) -> int:
    """USDC per step as integer micro-USDC, so no float or trailing-zero formatting reaches the hash."""
    micros = Decimal(str(price)) * 1_000_000
    if micros != micros.to_integral_value() or micros <= 0:
        raise ValueError("price must be positive with at most 6 decimals")
    return int(micros)


def provider_metadata(name: str, wallet: str, price: str | Decimal, capacity_mib: int | None) -> dict:
    if not isinstance(wallet, str) or not re.fullmatch(r"0x[0-9a-fA-F]{40}", wallet):
        raise ValueError("wallet must be a 0x-prefixed 20-byte address")
    return {
        "kind": META_KIND,
        "name": name.strip(),
        "wallet": wallet.lower(),
        "price_per_step_micros": price_micros(price),
        "capacity_mib": capacity_mib,
    }


def metadata_hash(meta: dict) -> str:
    return "0x" + keccak(canonical_bytes(meta)).hex()
