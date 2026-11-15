# Ekido roadmap: what to do next

Written 7 Nov 2026, after the ship. For the team and the next agent. Each item says why it matters, what "done" means, and roughly how big it is. The detailed state of the code is in `docs/agent-handoff.md`.

## Where we are

**Working and shown, as of 7 Nov:**

- **Recovery and payment on one laptop:** recovery after a kill, a cheating provider rejected and unpaid, memory adaptation, and payout only for accepted work on a local chain. On the RTX 3060, one recorded run.
- **Real GPU, no Docker (7 Nov):** the providers qualified on the 3060: A at 32 x 1, B at 8 x 4 under 768 MiB, C refused with a real out-of-memory, and P at 16 x 2. A full job wasn't run on this setup.
- **Cross-GPU round trip:** T4 → RTX 3060 → T4. The canary matched each time. One run.
- **Quality margin checked on the real model:** 5 seeds on a T4, 75 pairs, no false rejections.
- **Contract on Base Sepolia:** escrow `0x1BF65f755457a92850009c88AFb337Ec57745a22`, registry `0xcdf927CE0D885552529C5463993e64429a51c2Ff`. Settings were read back from the chain. The three wallets are funded with test ETH, and the client holds 20 test USDC.
- **Dashboard:** landing page, live and recorded modes, Verify page, receipts, and Prateek's earnings page. 105 tests.
- **One command to join as a provider,** for GPU or CPU: `python -m ekido_agent.join`. Tested by unit tests only, not across two machines.

**Not yet:** a job settled on Base Sepolia, a live provider on another machine, users running their own code, and a public server.

## Phase 1: before the demo (now to 13 Nov)

| # | Task | Why | Done when | Size |
|---|---|---|---|---|
| 1.1 | **One full GPU job on the dashboard,** on the laptop, with Start, Kill, the rejection, the payout and Verify | The demo story has never run end to end on the new dashboard and the no-Docker GPU stack | The run, recorded, with raw files in `experiments/results/` | 30 min |
| 1.2 | Run `experiments/rehearse.py` on that GPU stack, 5 rounds | Finds flaky failures before judges do | 5 of 5 clean | 1 hour |
| 1.3 | **Backup video** of 1.1 | If the laptop fails on stage | Video file | 30 min |
| 1.4 | Pitch and deck from `docs/judge-qa.md` and `docs/market-gaps.md` | Every number traces to a file | Deck reviewed by the team | Half a day |
| 1.5 | Rehearse the demo 10 times in a row | Gate G5 | 10 clean runs | Thu 12 Nov |
| 1.6 | Freeze on Mon 9 Nov night: bug fixes only after that | Protects the demo | — | — |

## Phase 2: real testnet money (after the demo, or before it if 1.1 to 1.3 are done)

| # | Task | Why | Done when | Size |
|---|---|---|---|---|
| 2.1 | Test the signed-payout path end to end on a local chain: `experiments/prepare_signed_job.py`, then the secure verifier | The previous agent built it but never ran it end to end. Base Sepolia jobs require it | A local job settles through it | 1 day |
| 2.2 | One real settlement on Base Sepolia, with A and B paid and P unpaid, visible on BaseScan | The strongest public proof | Explorer links in the handoff | Half a day, once 2.1 is done |
| 2.3 | Verify the contract source on BaseScan | Anyone can read the code they pay through | Green tick on BaseScan | 1 hour, needs a BaseScan API key |

## Phase 3: anyone can rent out a GPU (the decentralized part)

| # | Task | Why | Done when | Size |
|---|---|---|---|---|
| 3.1 | **Coordinator on a Google Cloud VM** with HTTPS, `API_TOKEN`, and verifiers on CPU | Providers anywhere can connect, with no laptop involved | `https://<server>/healthz` works, and the operator API is locked | 1 day. Needs a GCP project with billing, and `gcloud auth login` done by Piyush |
| 3.2 | Test `ekido_agent.join` from two other machines, one GPU and one CPU, on different networks | The one-command join is only unit-tested | Both run a job and get paid | Half a day |
| 3.3 | "Become a provider" page: connect a wallet, register on-chain (`ProviderRegistry.register` is open to anyone), set a price, copy the join command | No terminal knowledge needed to start | A new person joins from the page alone | 1 day |
| 3.4 | "Rent a GPU" page: available providers with GPU, price and history, then start a job and fund it from a wallet | The renter side of the marketplace | A job funded from the browser, end to end | 1 to 2 days |
| 3.5 | Spam and abuse limits: per-wallet limits, and a stake or deposit for providers | Open sign-up attracts junk accounts | Written policy and enforced limits | 1 day |

## Phase 4: users run their own code (`docs/custom-workloads.md`)

The client writes one `job.py` (`build_model`, `dataset_size`, `make_batch`). It runs only inside the provider's Docker sandbox, with no network, read-only, non-root and with resource limits, so the provider's computer stays safe.

| # | Task | Status |
|---|---|---|
| 4.1 | Runtime `custom-python/v1` | Written, **not tested** |
| 4.2 | Job spec rules | Written. Existing tests pass, no new tests |
| 4.3 | Agent: fetch the code and files by hash, mount them read-only, and refuse process mode | To do |
| 4.4 | Coordinator: client upload of code and files, stored by hash | To do |
| 4.5 | Verifier: evaluate custom jobs inside the same sandbox | To do. Without it, custom jobs can't pass the quality test |
| 4.6 | Dashboard: a "Your own code" option with file pickers | To do |
| 4.7 | Stronger isolation for strangers' code: gVisor or a VM | Later |

Size: about 3 to 5 days for 4.1 to 4.6.

## Phase 5: make it trustworthy at scale

- **Fair pay when a job fails:** accepted work is paid up to a cap agreed beforehand. It needs a contract change, and Arvind's review. See `docs/payment-incentives-analysis.md`, attack 2.
- **Minimum dispute window on-chain:** Arvind's diff is ready, in his review response.
- **Independent verifiers,** not run by the team, with their own stake.
- **A test set the client keeps private,** so providers can't train on the evaluation.
- **Hardware attestation** on GPUs that support it, and **encrypted checkpoints**.
- **A contract audit** before any real money.

## Decisions waiting on Piyush

1. GCP project and billing, for 3.1.
2. Whether 2.1 and 2.2 happen before the demo or after.
3. Whether to change the contract for fair pay on failure (Phase 5), and when.
