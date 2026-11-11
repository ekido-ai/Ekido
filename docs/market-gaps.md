# Market gaps: what GPUChain covers, and what it doesn't

Written 5 Nov 2026. **GPUChain can't honestly cover every gap in this market.** This page lists what we cover and what backs it, so nobody on the team over-claims in front of the judges.

Everything below "shown" comes from a real run or test in this repo. A blank in another product's documents doesn't prove it lacks a feature, and closed systems may do more.

## The one-sentence difference

We're not ahead as a GPU marketplace. What's different is a combination: **a job recovers across providers by itself, a quality test agreed before training decides whether the result counts, and on-chain escrow pays only for the work that survived into the accepted model.** We didn't find these three together in the sources we read. Don't say "only" or "first".

## Gaps we cover

| Gap in the market | What GPUChain does | Evidence | Limit |
|---|---|---|---|
| A provider dies and the renter restarts by hand, or loses the work | Detects the failure, picks the last accepted checkpoint, and resumes on another provider | RTX 3060 run: kill detected in under a second, 8 steps lost, resumed in about 50 s (`experiments/results/gpu_chain_story_20261105_001829.json`). Seven faults pass on CPU (`tests/test_e2e_faults.py`) | One seed on the GPU. Six faults haven't run on the GPU |
| "Completed" doesn't mean the model is any good | A statistical test, fixed on-chain by hash before training, decides the result | Poisoned provider rejected at 24.8% accuracy while reporting normal progress | Damage smaller than the margin can pass: 2 points at the final check, 5 mid-training. The evaluation set is public |
| Payment follows time, not useful work | Pays by accepted steps, split across providers. Rejected work earns zero, and the rest is refunded | Local chain: A 0.15, B 0.75, P nothing, 4.1 USDC refunded | Local chain so far, not Base Sepolia |
| A replacement with less memory can't run the job | Measures what fits, then changes the batching while keeping the same logical batch | Provider B ran 8 x 4 under a 768 MiB cap. Provider C was refused with a measured reason | One physical GPU with memory caps. **Not a different GPU model yet** |
| The renter has to trust the platform's payout figures | The **Verify** page reads the verdict from the transaction, recovers who signed, and recomputes the checkpoint chain and each payout in the browser | See `apps/web-combined/src/lib/verify/`, and the tamper results in `HANDOFF.md` | Doesn't prove training ran as claimed |
| Money stuck if the operator vanishes | Anyone can trigger a refund after the deadline. The contract requires verifier signatures for a payout | 85 contract tests, including Arvind's attacker review | Workers still trust coordinator-proposed payout inputs; see `docs/repo-review-2026-11-05.md`. Unaudited, testnet only |
| Rules changing after a job starts | The verifier set and arbiter are fixed per job | `contracts/test/AttackerReview.t.sol` | One admin key still controls future jobs |

## Built, but not proven yet

Say "built, not yet measured" for these. The first two are the most valuable things left to do.

| Item | What's missing | Who |
|---|---|---|
| Recovery on a truly different GPU | A real second GPU run through `experiments/cross_gpu_resume.py` | Vaibhav |
| Public settlement on Base Sepolia | Funded wallets, Arvind's re-check, and Piyush's go-ahead to deploy | Arvind, Piyush |
| Quality of a recovered run against an uninterrupted one | `experiments/quality_comparison.py`: 5 seeds on the real model | Vaibhav |
| False rejection on the real model | Measured on the synthetic workload only. Final checks: 0 of 8 at 2,000 examples, 2 of 8 at 512. Mid-training: 2 of 8 at a 0.02 margin, none at 0.03 or above. Needs `experiments/probation_noise.py --real` | Vaibhav |

## Gaps we don't cover

If a judge asks, say this first.

| Gap | Who's stronger | Why we don't cover it |
|---|---|---|
| GPU supply, price and scale | Akash, io.net, Vast.ai, RunPod | We run a demo network, not a marketplace |
| Proof that training ran correctly | Gensyn's Verde; Proof-of-Learning work | We test outcomes. Verde needs bitwise-reproducible execution, which recovery across different hardware breaks. The two approaches could work together |
| Privacy from a malicious provider | NVIDIA Confidential Computing on supported data-center GPUs | A provider sees the data and model in memory, and checkpoints aren't encrypted. **Public data only.** Never say "private training" |
| Independent verifiers | Bittensor-style validator networks; UMA or Kleros for disputes | Our three verifiers and arbiter are run by the team |
| No central coordinator | Prime Intellect's INTELLECT-1 for fault-tolerant training at scale | One coordinator schedules jobs. It can stall a job, and its payout proposal is currently trusted by the verifier workers |
| Proof of what hardware a provider has | Attested hardware on supported GPUs | Consumer GPU details are self-reported, and labelled by evidence level |
| Staking and slashing | EigenLayer-style systems | A cheating provider earns nothing, but loses no stake |
| A fair outcome for an honest provider when a job fails | Nobody we found solves this neatly | **A refused final model refunds everyone, including honest providers.** It's disclosed, and an open team decision |
| Any workload | SkyPilot and the marketplaces run general jobs | One allowlisted template, no user code, one GPU per job |

## Web3 at the core, and why a database wouldn't do

| What the chain does | Why it needs a chain |
|---|---|
| Holds the budget in escrow before any work starts | A client and provider who don't trust each other can see the money is really there |
| Fixes the job spec and quality policy by hash | Neither side can change the test after seeing the result |
| Accepts a verdict only with 2 of 3 registered verifier signatures (EIP-712) | Unsigned verdicts are refused; the workers need independent payout verification before this protects against a malicious coordinator |
| Commits the checkpoint lineage root and quality report hash | Anyone can later check that the payout rests on that exact work |
| Dispute window with a bond, and a permissionless timeout refund | Funds stay recoverable even if our servers are gone |

The chain doesn't make the compute itself trustworthy. That's the Quality Guard's job, and its limits are listed above.

## Current technology: used and deliberately not used

| Technology | Decision | Why |
|---|---|---|
| EIP-712 multi-signer verdicts, USDC, pull payments, Foundry 1.9, OpenZeppelin 5.7, viem | **Used** | In the running code and tests |
| ERC-8004 (agent identity, reputation, validation) | **Optional, after Base Sepolia works** | It's a Draft, its registry addresses still need checking at the source, and it leaves payments out of scope. It could publish provider reputation, kept apart from the money path. A failure in it must never block a payout |
| Ethereum Attestation Service | Not now | The verdict is already signed and anchored. It's a future way to publish reports |
| EIP-3009 gasless deposits | Not now | Nicer funding flow. Doesn't change the core story, and the contract is frozen for Arvind's re-check |
| zkML proofs of training | No | Not practical for training at this size today |
| Hardware attestation (TEE) | No | Documented for data-center GPUs. Don't assume it on an RTX 3060 |

## Sources

Read directly: [ERC-8004](https://eips.ethereum.org/EIPS/eip-8004), io.net, Akash and Vast.ai docs, and parts of [Proof-of-Learning with Incentive Security](https://arxiv.org/abs/2404.09005) and [SoK on decentralized AI](https://arxiv.org/abs/2411.17461). Through search summaries only: [Verde](https://arxiv.org/abs/2502.19405), UMA, Kleros, EigenLayer and NVIDIA Confidential Computing. Check those before quoting them. Nosana: nothing found beyond what `plan.md` cites. More sources are in `plan.md`.
