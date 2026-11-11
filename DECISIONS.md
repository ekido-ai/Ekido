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
