# Threat model

## Assets

- **Client budgets** locked in `GPUChainEscrow` (test USDC on Base Sepolia).
- **Provider earnings**, credited by the escrow and withdrawn by each provider.
- **Role keys:** coordinator, verifiers, arbiter and owner. Each sits in a root-only environment file on the server.
- **Checkpoints and their lineage**, which decide who gets paid for which steps.
- **Provider machines** that run training workloads.

## Trust boundaries and data flows

- **Providers** are trusted for nothing. Their telemetry is self-reported and never decides payment. Their checkpoints are signed, fenced and verified before anyone builds on them.
- **Verifiers** are trusted only as a quorum of 2 of 3, and only for the quality verdict and payout split.
- **The coordinator** orchestrates. It can start jobs and anchor event hashes, but cannot move funds.
- **The arbiter** resolves disputes inside the dispute window. If it stays silent, the verdict stands and the client's bond is returned.
- **The chain** enforces the money rules exactly as written.
- **The browser** reads the chain itself, so the money pages never depend on the coordinator telling the truth.

## Authentication and authorization

- People sign in with a wallet (EIP-4361). The message is verified in the browser, and the session lasts 8 hours. Demo views are read-only and cannot sign or move money.
- Providers join with a wallet-signed document. Every agent message is a signed envelope with a sequence number.
- The operator API answers only loopback or a holder of the API token.
- Verifier signatures are EIP-712, bound to chain id, contract, job id and an expiry.

## Threats and controls (STRIDE-style summary)

| Threat | Control | Tested in |
|---|---|---|
| Reentrancy on withdraw or finalize | Checks-effects-interactions, `ReentrancyGuard`, pull payments | `contracts/test/AttackerReview.t.sol` |
| Signature replay across chains, contracts or jobs | EIP-712 domain, job-bound verdicts, one-shot state, expiry | `contracts/test/GPUChainEscrow.t.sol`, `SignatureVector.t.sol` |
| Duplicate or malleable signatures | OpenZeppelin ECDSA, strictly ascending signers | Contract fuzz tests |
| Payouts that don't add up | `sum(payouts) + fee + refund == budget`; invariant `balance == locked + withdrawable` | Invariant tests in `contracts/test/` |
| Coordinator moving funds | Role checks: it can only mark active and anchor events | Access-control tests |
| Funds locked forever | Permissionless timeout refund after deadline plus grace | Time-warp tests, `TimestampEdge.t.sol` |
| Zombie worker writing after being replaced | Fencing token per attempt (409 on stale writes), dead-man lease | Coordinator fencing tests, e2e fault tests |
| Malicious checkpoint (pickle, wrong shapes, NaN, oversized) | safetensors and JSON only, validation order before any load | `packages/ekido_core/tests` (GPCK) |
| Provider poisons weights or skips training | Paired bootstrap test against the last accepted checkpoint, weight-change check, rollback | Quality tests, recorded 4 Nov run |
| Lying coordinator shown to the client | Browser recomputes payouts and lineage from the chain; tampering is flagged | `apps/web-combined/src/lib/verify`, `experiments/results/verify_tamper_20261105.json` |
| Fake providers flooding the network | At most 5 providers per IP, unique printable names, rate limits | `apps/coordinator/tests/test_provider_join.py`, `test_rate_limit.py` |
| XSS, clickjacking, mixed content | Strict CSP with `connect-src` allowlist, `X-Frame-Options: DENY`, HSTS, `nosniff` | `next.config.ts` headers, Caddy `(secure)` snippet |
| Job escapes onto a provider's machine | Approved workloads only; Docker mode with no network, read-only root, dropped capabilities, memory and PID limits | Agent tests |
| Disk loss on the server | Daily integrity-checked backups copied to a private bucket the server cannot delete from | Backup run of 10 Nov |

## Contract security pass (14 Nov 2026)

Static analysis, fuzz and invariant results for `contracts/src/`. Not an audit. The full triage is in [`contracts/security/slither-report.md`](contracts/security/slither-report.md) and the raw output in `contracts/security/slither-output.txt`.

| Check | Result |
|---|---|
| Slither 0.11.6 (102 detectors, solc 0.8.33) | 12 results: 0 High, 2 Medium, 7 Low, 3 Informational. Both Medium results are false positives (locals that deliberately start at their default value); the rest are timestamp comparisons and unindexed event addresses. No code change needed |
| Invariant `invariant_contractIsAlwaysSolvent` | Token balance equals `totalLocked + totalWithdrawable` across random call sequences (128 runs, depth 64) |
| Fuzz `testFuzz_settlementConservesFunds`, `testFuzz_wrongTotalAlwaysRejected` | Payouts plus refund always equal the budget; a verdict whose amounts don't add up is always rejected (512 runs each) |

Weaknesses found in the earlier attacker review, each reproduced by a test in `contracts/test/AttackerReview.t.sol`:

| ID | Weakness | Status |
|---|---|---|
| F1 | The client picks the deadline, and anyone can refund the client an hour after it, even while the job is still running. A verdict that is signed but not yet submitted then fails | Open, disclosed. The coordinator must check the on-chain deadline and submit the verdict in time (`test_poc_F1_clientRefundsBeforeLateVerdictLands`) |
| F2 | The arbiter could be swapped during a dispute | Fixed: the arbiter is snapshotted per job (`test_holds_F2_*`, `IndependentF2F5.t.sol`) |
| F3 | A client can delay provider payouts by up to 3 days at no cost if the arbiter stays silent | Open, disclosed (`test_poc_F3_freeDisputeDelaysProviderPayoutThreeDays`) |
| F4 | Job IDs are first come, first served, so a pending `createJob` can be front-run. The attacker can't take the money | Open, disclosed (`test_poc_F4_attackerSquatsJobId`) |
| F5 | A job could be activated after its deadline | Fixed: `markActive` checks the deadline (`test_holds_F5_cannotActivateAfterDeadline`) |
| F6 | The owner is one key with no delay and can change the coordinator, arbiter and verifier set for new jobs | Open, disclosed (`test_poc_F6_ownerSwapIsInstantAndUntested`) |

## Out of scope / residual

- **Colluding verifiers.** Two of the three team-run verifiers could approve bad work. The dispute window and public report hashes are the only defence today; independent paid verifiers are next.
- **Private data.** Without confidential hardware, a provider can read training data in GPU memory. Use public data only.
- **Proof of hardware.** Consumer GPUs can't prove what they are; benchmarks are measured but self-run.
- **Training on the evaluation set.** A provider can train on the public test set. The fix is an evaluation set the client keeps private.
- **The single coordinator VM.** It can stall scheduling but cannot take funds; the timeout refund protects clients.
- **The contracts are unaudited.** Testnet only.
