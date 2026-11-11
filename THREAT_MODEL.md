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
| Malicious checkpoint (pickle, wrong shapes, NaN, oversized) | safetensors and JSON only, validation order before any load | `packages/gpuchain_core/tests` (GPCK) |
| Provider poisons weights or skips training | Paired bootstrap test against the last accepted checkpoint, weight-change check, rollback | Quality tests, recorded 4 Nov run |
| Lying coordinator shown to the client | Browser recomputes payouts and lineage from the chain; tampering is flagged | `apps/web-combined/src/lib/verify`, `experiments/results/verify_tamper_20261105.json` |
| Fake providers flooding the network | At most 5 providers per IP, unique printable names, rate limits | `apps/coordinator/tests/test_provider_join.py`, `test_rate_limit.py` |
| XSS, clickjacking, mixed content | Strict CSP with `connect-src` allowlist, `X-Frame-Options: DENY`, HSTS, `nosniff` | `next.config.ts` headers, Caddy `(secure)` snippet |
| Job escapes onto a provider's machine | Approved workloads only; Docker mode with no network, read-only root, dropped capabilities, memory and PID limits | Agent tests |
| Disk loss on the server | Daily integrity-checked backups copied to a private bucket the server cannot delete from | Backup run of 10 Nov |

## Out of scope / residual

- **Colluding verifiers.** Two of the three team-run verifiers could approve bad work. The dispute window and public report hashes are the only defence today; independent paid verifiers are next.
- **Private data.** Without confidential hardware, a provider can read training data in GPU memory. Use public data only.
- **Proof of hardware.** Consumer GPUs can't prove what they are; benchmarks are measured but self-run.
- **Training on the evaluation set.** A provider can train on the public test set. The fix is an evaluation set the client keeps private.
- **The single coordinator VM.** It can stall scheduling but cannot take funds; the timeout refund protects clients.
- **The contracts are unaudited.** Testnet only.
