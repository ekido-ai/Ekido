# Shared Schemas (v1)

These files are the contract between the four tracks, so everyone can build against them in parallel.

**Status: draft until Piyush confirms the freeze on 4 Nov.** After that, changes go through Piyush, because they affect every track.

| File | Used by | What it defines |
|---|---|---|
| `job_spec.schema.json` | Web, coordinator, runtime | The workload: immutable for the whole job |
| `quality_policy.schema.json` | Web, coordinator, verifier | Acceptance terms, fixed before execution |
| `exec_config.schema.json` | Compiler, runtime | The part that may change per GPU |
| `gpck_manifest.schema.json` | Runtime, coordinator, verifier | Checkpoint manifest (GPCK/1) |
| `adaptation_manifest.schema.json` | Compiler, coordinator, web | Why a GPU was accepted or rejected, and what changed |
| `agent_envelope.schema.json` | Agent, coordinator | Signed agent messages, plus the message type list |
| `quality_report.schema.json` | Verifier, coordinator, web | One verifier's signed evaluation |
| `events.schema.json` | Coordinator, web | Dashboard events over WebSocket, and replay files |
| `verdict.eip712.json` | Verifier, coordinator, contract | The typed data that releases payment |

## Conventions

- **Hashes:** lowercase hex SHA-256 with no `0x` (`sha256` in `$defs` of the schemas). On-chain values use `0x`-prefixed `bytes32`.
- **Canonical JSON:** RFC 8785 (JCS). A document's hash is the SHA-256 of its canonical form, with the `signature` and `sig` fields removed.
- **Addresses:** `0x`-prefixed, 20 bytes, compared case-insensitively.
- **Amounts:** USDC base units (6 decimals) as decimal strings, never floats.
- **Times:** RFC 3339 UTC.
- **Unknown values:** use `null` or leave the field out. Never use `0` to mean unknown, because the UI shows these numbers.
- **Unknown fields are rejected** (`additionalProperties: false`), so typos fail early.

## How the Verdict is built

`contracts/src/GPUChainEscrow.sol` is the contract we use. `ekido_core/settlement.py` builds the Verdict, so every verifier signs identical bytes:

- `finalCheckpoint`: the final GPCK manifest hash.
- `lineageRoot`: hash over the accepted manifest hashes, in order from root to tip.
- `qualityReport`: hash over the quorum's report hashes, sorted and de-duplicated. Verifiers can't sign a single report's hash, because reports differ slightly across devices.
- `payees`: sorted by numeric address. Provider payouts are `accepted steps x rate`, and the rest is the client's `refund`.
- A failed verdict has no payees and refunds the whole budget.

**Flow:** verifiers submit signed reports, the coordinator derives the Verdict, then each verifier re-derives it, checks it, and signs it.

## Rules these schemas encode

- A logical step means the same thing on every GPU: `logical_batch_size` is in `job_spec`, and `micro_batch` and `accumulation` are in `exec_config`.
- `micro_batch * accumulation` must equal `logical_batch_size`. JSON Schema can't express this, so the shared library checks it.
- Master weights and optimizer state are always FP32, and only autocast (`amp`) varies.
- `kind` and `label` fields exist so the UI can't present a simulated thing as real.
