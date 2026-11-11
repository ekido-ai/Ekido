"""Signing for manifests, agent messages and settlement verdicts. Requires eth-account.

Two schemes:
- EIP-191 over a document's canonical hash, for off-chain documents.
- EIP-712 for the settlement verdict, which GPUChainEscrow verifies on-chain.
"""

from __future__ import annotations

from eth_account import Account
from eth_account.messages import encode_defunct, encode_typed_data
from eth_utils import keccak

from .canonical import document_hash

VERDICT_TYPES = {
    "Verdict": [
        {"name": "jobId", "type": "bytes32"},
        {"name": "passed", "type": "bool"},
        {"name": "finalCheckpoint", "type": "bytes32"},
        {"name": "lineageRoot", "type": "bytes32"},
        {"name": "qualityReport", "type": "bytes32"},
        {"name": "payees", "type": "address[]"},
        {"name": "amounts", "type": "uint256[]"},
        {"name": "refund", "type": "uint256"},
        {"name": "expiry", "type": "uint64"},
    ]
}


def _hex(value: bytes) -> str:
    return "0x" + bytes(value).hex()


def _domain(chain_id: int, contract: str) -> dict:
    return {"name": "GPUChainEscrow", "version": "1", "chainId": chain_id, "verifyingContract": contract}


def _verdict_message(verdict: dict, chain_id: int, contract: str):
    return encode_typed_data(domain_data=_domain(chain_id, contract), message_types=VERDICT_TYPES, message_data=verdict)


def verdict_digest(verdict: dict, chain_id: int, contract: str) -> str:
    """The value GPUChainEscrow.hashVerdict returns for the same input."""
    message = _verdict_message(verdict, chain_id, contract)
    return _hex(keccak(b"\x19" + message.version + message.header + message.body))


def sign_verdict(verdict: dict, chain_id: int, contract: str, private_key: str) -> str:
    return _hex(Account.sign_message(_verdict_message(verdict, chain_id, contract), private_key).signature)


def recover_verdict_signer(verdict: dict, chain_id: int, contract: str, signature: str) -> str:
    return Account.recover_message(_verdict_message(verdict, chain_id, contract), signature=signature)


def order_signatures(verdict: dict, chain_id: int, contract: str, signatures: list[str]) -> list[str]:
    """Ascending by signer, as the contract requires. Duplicate signers are dropped."""
    by_signer = {recover_verdict_signer(verdict, chain_id, contract, s).lower(): s for s in signatures}
    return [by_signer[signer] for signer in sorted(by_signer, key=lambda a: int(a, 16))]


def sign_document(document: dict, private_key: str) -> tuple[str, str]:
    """Signs the canonical hash. Returns (signer address, signature). `signature` and `sig` fields are excluded."""
    account = Account.from_key(private_key)
    signed = Account.sign_message(encode_defunct(hexstr=document_hash(document)), private_key)
    return account.address, _hex(signed.signature)


def recover_document_signer(document: dict, signature: str) -> str | None:
    """Returns the signer's address, or None for an unusable signature. Callers compare it to who they expect."""
    try:
        return Account.recover_message(encode_defunct(hexstr=document_hash(document)), signature=signature)
    except Exception:  # eth-account raises several types on malformed input; all mean the same here.
        return None


def verify_document(document: dict, signature: str, expected_signer: str) -> bool:
    signer = recover_document_signer(document, signature)
    return signer is not None and signer.lower() == expected_signer.lower()
