"""Build and check EOA-signed terms for the independent payout protocol."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

from eth_account import Account

from .canonical import document_hash
from .signing import sign_document, verify_document

ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}\Z")
MAX_PROVIDERS = 256


def new_job_ids(client_address: str) -> tuple[str, str]:
    """Allocate IDs locally before collecting quotes; no coordinator trust needed."""
    if not isinstance(client_address, str) or not ADDRESS.fullmatch(client_address):
        raise ValueError("invalid client address")
    job_id = str(uuid4())
    return job_id, onchain_job_id(job_id, client_address)


def onchain_job_id(job_id: str, client_address: str) -> str:
    if not isinstance(client_address, str) or not ADDRESS.fullmatch(client_address):
        raise ValueError("invalid client address")
    try:
        parsed = UUID(job_id)
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("invalid job ID") from exc
    if parsed.version != 4 or str(parsed) != job_id:
        raise ValueError("job ID must be a canonical random UUIDv4")
    return "0x" + document_hash({"job": job_id, "client": client_address.lower()})


def signed_document(body: dict, key: str) -> dict:
    return dict(body, signature=sign_document(body, key)[1])


def workload_hash(spec: dict) -> str:
    """Hash the workload before quotes are inserted, avoiding a hash cycle."""
    return document_hash({key: value for key, value in spec.items() if key != "provider_terms"})


def provider_quote(*, job_id: str, onchain_id: str, chain_id: int, contract: str, provider_id: str, rate: str, workload: str, key: str) -> dict:
    wallet = Account.from_key(key).address.lower()
    if not isinstance(workload, str) or not re.fullmatch(r"[0-9a-f]{64}", workload):
        raise ValueError("invalid workload hash")
    return signed_document({"kind": "gpuchain.provider_quote.v1", "job_id": job_id, "onchain_job_id": onchain_id, "chain_id": chain_id, "contract": contract.lower(), "provider_id": provider_id, "wallet": wallet, "price_per_step": str(rate), "workload_hash": workload}, key)


def job_binding(*, job_id: str, onchain_id: str, chain_id: int, contract: str, spec: dict, policy: dict, budget: str, key: str) -> dict:
    return signed_document({"kind": "gpuchain.job_binding.v1", "job_id": job_id, "onchain_job_id": onchain_id, "chain_id": chain_id, "contract": contract.lower(), "spec_hash": document_hash(spec), "policy_hash": document_hash(policy), "budget": str(budget)}, key)


def validate_terms(*, job_id: str, client: str, binding: dict, spec: dict, policy: dict, budget: Decimal, chain_id: int, contract: str) -> None:
    """Reject unsigned, inconsistent or malformed terms before work starts."""
    try:
        if type(chain_id) is not int or chain_id <= 0 or not isinstance(contract, str) or not ADDRESS.fullmatch(contract):
            raise ValueError("invalid chain configuration")
        if not isinstance(budget, Decimal) or not budget.is_finite() or budget <= 0 or budget * 1_000_000 != (budget * 1_000_000).to_integral_value():
            raise ValueError("invalid budget: it must be positive, with at most 6 decimals")
        onchain_id = onchain_job_id(job_id, client)
        expected = {"kind": "gpuchain.job_binding.v1", "job_id": job_id, "onchain_job_id": onchain_id, "chain_id": chain_id, "contract": contract.lower(), "spec_hash": document_hash(spec), "policy_hash": document_hash(policy)}
        if any(binding.get(k) != v for k, v in expected.items()) or Decimal(str(binding["budget"])) != budget or not verify_document(binding, binding["signature"], client):
            raise ValueError("invalid client job binding")
        terms = spec["provider_terms"]
        if not isinstance(terms, list) or not 0 < len(terms) <= MAX_PROVIDERS:
            raise ValueError("invalid provider terms count")
        seen = set()
        for term in terms:
            pid, wallet, rate, quote = term["provider_id"], term["wallet"], Decimal(str(term["price_per_step"])), term["quote"]
            if not isinstance(pid, str) or not pid or len(pid) > 128 or pid in seen or not isinstance(wallet, str) or not ADDRESS.fullmatch(wallet):
                raise ValueError("invalid provider identity")
            if not rate.is_finite() or rate < 0 or rate * 1_000_000 != (rate * 1_000_000).to_integral_value():
                raise ValueError("invalid provider rate")
            expected_quote = {"kind": "gpuchain.provider_quote.v1", "job_id": job_id, "onchain_job_id": onchain_id, "chain_id": chain_id, "contract": contract.lower(), "provider_id": pid, "wallet": wallet.lower(), "workload_hash": workload_hash(spec)}
            if any(quote.get(k) != v for k, v in expected_quote.items()) or Decimal(str(quote["price_per_step"])) != rate or not verify_document(quote, quote["signature"], wallet):
                raise ValueError("invalid provider quote")
            seen.add(pid)
    except (KeyError, TypeError, AttributeError, InvalidOperation) as exc:
        raise ValueError("malformed signed job terms") from exc
