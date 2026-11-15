# Decisions log — GPUChain

The choices that shaped the project, with the reason for each. The original planning document with the full research is [`plan.md`](plan.md).

## Scope and claims

| Decision | Why |
|---|---|
| Verify **outcomes** statistically, not execution | Recovery on a different GPU breaks bitwise determinism, which execution-verification systems rely on. A paired test of the model's quality still works across GPUs. |
| Never claim "trustless", "any GPU", "zero downtime", "proven equivalence" or "private training" | None of them is true for this prototype. Verifiers are team-run, only NVIDIA (and CPU) is supported, recovery takes about a minute, and providers can read GPU memory. |
| Every number traces to a raw file in `experiments/results/` | Pitch numbers must survive a judge asking "where is that from?". CPU or synthetic runs are always labelled and never presented as GPU evidence. |
| Rule-based failure detection, not an "AI predictor" | There is no failure data to train a predictor honestly. |
| Name providers by real capacity, never by a GPU we don't have | A "simulated H100" running on an RTX 3060 would mislead. Memory caps on one GPU are labelled as such. |

## Training and checkpoints

| Decision | Why |
|---|---|
| DistilBERT + LoRA on AG News as the first workload | Small checkpoints, no BatchNorm, a per-example metric, and fast enough to train and recover on a laptop GPU. |
| A custom training loop, not Trainer or Accelerate | Exact control of logical steps, and no pickle anywhere in the checkpoint path. |
| The logical-step invariant | The logical batch, LR schedule, seed and data order never change; only micro-batch, accumulation and precision adapt. Gradient scale is `mean_loss × n_micro / L`; master weights stay FP32. |
| BF16 only when compute capability ≥ 8 | `torch.cuda.is_bf16_supported()` returns True through emulation on a T4. |
| GPCK checkpoints: safetensors + signed canonical JSON | Signed lineage and fencing tokens make every checkpoint attributable; safetensors removes the pickle attack surface (CVE-2025-32434). |
| A real memory probe before any placement | Estimates never approve a configuration; only a measured forward, backward and optimizer step under 85% of capacity does. |
| Quality gate: paired bootstrap, one-sided 95% bound ≥ −2 points, 2,000 examples | On 872 examples the 95% interval is about ±2 points, so the test would measure noise. Margin and set are fixed by hash before training. |

## Money and chain

| Decision | Why |
|---|---|
| Base Sepolia with Circle's test USDC | A low-fee Ethereum L2 and a dollar stablecoin; hosts get paid in dollars, not a volatile token. |
| No GPUChain token | Emissions pay nodes for existing and invite fake nodes. Every payout comes from a client budget. |
| Two contracts: escrow and registry | The registry holds no funds, so a bug there can't drain money. No upgradeability. |
| 2-of-3 EIP-712 verifier quorum, dispute window with a bond, arbiter | Neither the coordinator nor a single verifier can decide payouts alone. |
| Permissionless timeout refund | If the operator vanishes, clients still get their money back. |
| Pull payments, at most 8 payees | No reentrancy through payouts and bounded gas. |
| Pay by accepted lineage | Each provider earns for steps that survive into the accepted model; rejected and unsaved steps earn nothing, which rewards honest checkpointing. |
| 8% protocol fee on accepted work only | Sustainable without a token, aligned with the client (no fee on a failed job), and still about 8% under typical market rates per accepted hour. Providers keep 100% of their price. |
| Providers commit their own terms on-chain (`keccak256` of RFC 8785 JSON) | Anyone can check that the coordinator shows a provider's terms exactly as the provider set them. |
| The browser recomputes the books from the chain | Proof of reserves and a 5-way reconciliation mean no one has to trust the coordinator's numbers. An indexer speeds this up, and the browser rescans the chain if anything disagrees. |

## Product and operations

| Decision | Why |
|---|---|
| Wallet sign-in (EIP-4361), no passwords | Nothing secret to store or leak; withdrawals ask the wallet again. Read-only demo accounts let anyone look around without a wallet. |
| One-command provider kit for Windows, macOS and Linux | Supply only grows if a gamer can join in minutes. The kit is plain Python source with a published SHA-256. |
| One VM, SQLite, systemd, Caddy | The fewest moving parts that run reliably. Postgres, job leases and a second coordinator are the next step (see `docs/system-design.md`). |
| Off-site backups the server cannot delete | Protects against disk loss and against an attacker on the server wiping backups. |
| Email alerts from external uptime checks | Someone hears about an outage even when the server itself is down. |

## Decisions made on 14 Nov 2026

### 1. A refused final model fails the whole job: keep it

When the final model is refused by the quality test, the job fails and everyone is refunded, including providers who did honest work earlier in the run.

| Option | What it means | Cost |
|---|---|---|
| A. Full refund (kept) | Simple to explain. A bad final model costs the client nothing. | A provider can do honest work and earn 0 because a later one was bad. |
| B. Pay accepted steps, refuse the rest | Providers keep pay for steps that passed their own checks. | Needs a rule for which steps count, plus a contract and verdict change. Weakens "pay only for what works". |
| C. Full refund, plus a small payment for accepted checkpoints from a fee pool | Honest providers get something. | A new pool and a new place to cheat. |

Decision: keep A. It matches the promise "pay only for what works" and needs no contract change; the README limitation says it plainly. Revisit B after the contracts are audited.

## Decisions made on 15 Nov 2026

### 1. Rename GPUChain to Ekido, everything except what is signed or deployed

"GPUChain" was generic. **Ekido** comes from the Japanese *ekiden*, a relay where a sash passes from runner to runner, which is what a job does here.

| Option | What it means | Cost |
|---|---|---|
| A. Rename the brand only | Only README, docs and UI change | Code keeps saying `gpuchain`, which confuses every new contributor |
| B. Rename everything except what is signed or deployed (kept) | Packages, imports, env vars, CI, docs and UI all change. Signed identifiers stay | A short, documented list of leftovers |
| C. Rename everything, contract included | The contract name and its EIP-712 domain change | Means redeploying the contract, and breaks every signature and hash that is already recorded |

Decision: B.
- **Changed:** packages are now `ekido_*`, env vars use the `EKIDO_` prefix, and the kit is `ekido-provider-kit.zip`.
- **Kept, because they are signed, hashed or deployed:** `GPUChainEscrow`, its EIP-712 domain, `gpuchain.*.v1` and `gpuchain-replay/1`. A future protocol version can move to `ekido.*` with a version bump.
- **Kept, because changing them would break users:** browser storage keys, and the `gpuchain_hf_cache` volume (renaming it would re-download every provider's models).
- **Moving later, with the server migration:** the live domain, unit names, server paths and `~/.gpuchain/`.

### 2. Product direction for Ekido

The full set of landmark decisions is recorded in `docs/ekido/`: who we build for, selling results instead of compute, phones as providers, hidden providers, fiat by default with blockchain proofs, the AI assistant, and the roadmap. In short:
- We build for small businesses, developers and personal users who want their own small model.
- Payment is in normal money by default, the blockchain stores proof, and crypto is optional.
