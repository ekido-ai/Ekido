# Ekido

**Train on spare GPUs. Pay only for what works.**

*Formerly GPUChain.* The name comes from the Japanese *ekiden*, a relay race where a sash passes from runner to runner: here, a training job passes from device to device without losing its work. The escrow contract deployed on Base Sepolia keeps its original name, `GPUChainEscrow`, because the name is part of its signatures. So do the signed message kinds (`gpuchain.*.v1`), so that earlier jobs and records still verify.

Ekido is a prototype GPU network for model training with three guarantees:

- **Survives:** when a provider's GPU dies mid-run, the job moves to another GPU from its last trusted checkpoint, adapting micro-batch, gradient accumulation and precision to the new GPU's memory while keeping every logical training step the same.
- **Refuses:** a statistical quality test, fixed by hash before training starts, refuses bad work before anyone is paid. Two of three verifiers must sign.
- **Settles:** the client's USDC budget waits in an escrow contract on Base Sepolia. Each provider is paid per accepted step, an 8% protocol fee applies only to accepted work, and the rest is refunded. Anyone can recompute every payout from the chain in their own browser.

Live on the Base Sepolia testnet: <https://gpuchain.duckdns.org> (test USDC only; unaudited contracts).

## What has actually run

Every number here traces to a raw file in [`experiments/results/`](experiments/results/).

| Result | Where it ran | Source |
|---|---|---|
| Provider killed mid-run: noticed in 0.6 s, training resumed elsewhere 65 s later, 8 of 400 steps lost, final accuracy 90.7% on 2,000 test examples | RTX 3060 Laptop, local chain | `recording_job_4f605443_20261104/` |
| A replacement returned junk (24.8% vs 89.2%); it was refused and paid 0 | same run | same |
| 3 of 3 kill-and-recover rounds settled cleanly | RTX 3060 Laptop, local chain | `rehearsal_20261109_190928.json` |
| One run handed Tesla T4 → RTX 3060 → T4, accuracy 89.6% → 90.6% → 90.5%, canary loss matched | two machines | `external_t4_leg1_20261105/`, `leg2_3060_20261107/`, `external_vaibhav_leg3_20261107/` |
| Resuming with micro-batch 32 → 8: mean change +0.09 points, 95% CI [−0.16, +0.34], 5 seeds | Tesla T4 | `external_vaibhav_t4_20261106/` |
| A real settlement: 0.15 test USDC locked, 0.12 paid, 0.03 refunded | Base Sepolia (a small CPU verification job) | escrow `0x1BF65f755457a92850009c88AFb337Ec57745a22` |

Not shown: recovery between GPUs live on stage, independent (non-team) verifiers, private training data, an audit.

## Reliability: what happens when a GPU fails

Spare GPUs go away without warning: a laptop sleeps, a driver crashes, a cloud instance is reclaimed. Ekido treats that as the normal case.

| Failure | How it is noticed | What the system does |
|---|---|---|
| Provider process or machine dies | Heartbeats stop; the coordinator's lease on the provider runs out | The job moves to another provider and resumes from the last checkpoint the verifiers accepted |
| Network drops | The agent's connection closes | Same failover; a fencing token stops the old provider's late work from being accepted |
| Out of memory on the new GPU | A memory probe before training | Micro-batch, accumulation and precision change; every logical step stays the same |
| Crash while writing a checkpoint, or a corrupt checkpoint | Content hash and parent link on every checkpoint | The checkpoint is refused and the run fails over, so the chain of checkpoints cannot break |
| Provider returns bad work | Verifiers re-evaluate on held-out data; two of three must sign | The work is refused and that provider is paid 0 |
| Agent restarts with a new key | Every key a provider has used is kept | Accepted work is still paid |

Measured on one run (RTX 3060 Laptop, local chain, raw files in `experiments/results/`):

- Failure noticed in **0.6 s**; training resumed on another provider **65 s** later.
- **8 of 400** steps lost; final accuracy 90.7% on 2,000 test examples.
- 3 of 3 kill-and-recover rounds settled with the right payouts.

What this does not show yet: these are single runs on one seed; six fault types are covered by end-to-end tests on CPU (`tests/test_e2e_faults.py`) but have not all been run on a GPU; recovery between two physical GPUs has run as a handed-over job, not live in front of an audience.

## How it fits together

```
Client (web app + wallet) ──► Coordinator ◄──WSS── GPU providers (agent + runtime)
                                  │  ▲
                                  ▼  │
                       Verifiers (2 of 3, EIP-712)
                                  │
                                  ▼
            GPUChainEscrow + ProviderRegistry on Base Sepolia
```

The chain holds the money and the rules; the coordinator orchestrates recovery, scheduling and settlement; the browser re-checks everything against the chain. Full analysis: [`docs/system-design.md`](docs/system-design.md).

## Repository layout

| Path | What it is |
|---|---|
| `packages/ekido_core/` | Shared Python library: schemas, canonical JSON, signing, checkpoints (GPCK), elastic compiler, quality statistics, protocol fee |
| `contracts/` | Foundry project: `GPUChainEscrow` and `ProviderRegistry` |
| `workers/runtime/` | Training runtime: logical-step training loop, checkpoints, memory probe |
| `workers/agent/` | Provider agent: join, telemetry, process/Docker spawning, signing, on-chain listing |
| `workers/verifier/` | Independent evaluation, payout recomputation and EIP-712 signing |
| `apps/coordinator/` | FastAPI coordinator: jobs, recovery, scheduler, artifacts, settlement, chain indexer, rate limits |
| `apps/web-combined/` | Next.js web app: landing, mission control, on-chain books, accounts, provider onboarding |
| `apps/web/` | The first dashboard prototype |
| `infra/` | Provider kit, GCP deployment and ops (backups, monitoring), Docker files, test runners |
| `experiments/` | Spikes, benchmarks and the raw results behind every claim |
| `tests/` | End-to-end and fault scenarios |
| `docs/` | Design, security and privacy, market research, business model, schemas |

## Running it

- **Rent out a GPU:** download the provider kit from the website's *Rent out your GPU* page, or build it with `python infra/provider-kit/build_kit.py`, then follow `infra/provider-kit/README.md`.
- **Tests:** contracts with `forge test` in `contracts/`; Python packages with `pytest` in each package; the web app with `npx vitest run` in `apps/web-combined/`. On Windows, `infra/run-tests-host.ps1` runs the CPU suites with a memory watchdog.
- **Local demo:** see [`docs/demo-runbook.md`](docs/demo-runbook.md) for the GPU path and the CPU fallback.
- **Deploys:** merging into `main` deploys itself once CI is green; see [`RUNBOOK.md`](RUNBOOK.md).

Never commit `.env` files or private keys. Use testnet-only wallets.

## Limitations

This is a prototype on a test network. Contracts are unaudited. Verifiers and the dispute arbiter are run by the team, so verification is permissioned, not trustless. Providers can read job data in GPU memory, so only public data should be used. A pass from the quality test means no degradation was detected beyond the agreed margin, not that two models are identical.

## Team

| | Role |
|---|---|
| Piyush Garg | Team lead: coordinator, recovery, settlement, infrastructure and integration |
| Vaibhav Parmar | ML runtime: training runtime, checkpoints, cross-GPU runs on T4 and RTX 3060 |
| Arvind Kushwaha | Smart contracts: escrow and registry contracts, verifiers, Base Sepolia deployment |
| Prateek Sharma | Product design: web app, UI/UX, the demo |

Built for a hackathon in November 2026 and continued as a personal project.

## License

All rights reserved. The source is here to read; using, copying or deploying it needs written permission. See [`LICENSE`](LICENSE).
