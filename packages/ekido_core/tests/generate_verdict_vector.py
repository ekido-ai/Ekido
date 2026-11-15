"""Writes the shared test vector that contracts/test/SignatureVector.t.sol also checks.

If Python and Solidity ever disagree on the digest, verifier signatures stop working on-chain,
so both sides are tested against this one file. The keys are public test values with no funds.
"""

import json
import sys
from pathlib import Path

from eth_account import Account

from ekido_core.signing import sign_verdict, verdict_digest

CHAIN_ID = 84532
CONTRACT = "0x00000000000000000000000000000000000C0DE1"
KEYS = ["0x" + f"{i:064x}" for i in (11, 22, 33)]

VERDICTS = {
    "passed_two_payees": {
        "jobId": "0x" + "ab" * 32,
        "passed": True,
        "finalCheckpoint": "0x" + "01" * 32,
        "lineageRoot": "0x" + "02" * 32,
        "qualityReport": "0x" + "03" * 32,
        "payees": ["0x00000000000000000000000000000000000000A1", "0x00000000000000000000000000000000000000B2"],
        "amounts": [2_000_000, 2_500_000],
        "refund": 500_000,
        "expiry": 1_900_000_000,
    },
    "failed_no_payees": {
        "jobId": "0x" + "cd" * 32,
        "passed": False,
        "finalCheckpoint": "0x" + "00" * 32,
        "lineageRoot": "0x" + "04" * 32,
        "qualityReport": "0x" + "05" * 32,
        "payees": [],
        "amounts": [],
        "refund": 5_000_000,
        "expiry": 1_900_000_000,
    },
}


def build() -> dict:
    cases = []
    for name, verdict in VERDICTS.items():
        cases.append(
            {
                "name": name,
                "verdict": verdict,
                "digest": verdict_digest(verdict, CHAIN_ID, CONTRACT),
                "signers": [Account.from_key(k).address for k in KEYS],
                "signatures": [sign_verdict(verdict, CHAIN_ID, CONTRACT, k) for k in KEYS],
            }
        )
    return {"chain_id": CHAIN_ID, "contract": CONTRACT, "cases": cases}


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
