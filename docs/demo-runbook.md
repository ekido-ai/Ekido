# Demo Runbook

**Current status:** the synthetic CPU demo now creates signed local-only provider terms and uses secure verifiers; a no-kill job was tested through settlement on a local Anvil chain. The GPU demo and recovery after a kill still need to be rehearsed with this launcher change. Automatic signing uses public demo keys and is restricted to local chain 31337. Testnet job creation requires separately collected provider quotes and a client binding; do not use the demo keys or unsafe local verifier mode for real funds.

For the live demo in front of judges. Rehearse from this file exactly, and change it when reality differs.

## One time setup, per laptop

Needs Docker Desktop with GPU support, Node, and Python. From the repo root:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install "fastapi>=0.115" "uvicorn>=0.30" "sqlalchemy>=2" pydantic-settings eth-account websockets web3
docker build -t gpuchain-runtime:spike -f infra/runtime.Dockerfile infra
cd apps/web; pnpm install; pnpm build; cd ../..
```

Run `experiments/spike_feasibility.py` once while online (see `experiments/README.md`), so the model and data are cached.

## Before going on stage (about 5 minutes)

1. **Close the browser's extra tabs and other apps.** A run was stopped at 1.9 GB of free memory.
2. Plug in AC power, and use a cooling pad. The GPU has reached 88°C.
3. Start Docker Desktop.
4. Check everything:
   ```powershell
   .\.venv\Scripts\python.exe infra\preflight.py
   ```
5. Start the stack in its own terminal, and wait for `READY`. Qualifying providers takes about 2 minutes:
   ```powershell
   .\.venv\Scripts\python.exe experiments\demo_stack.py
   ```
6. Start the dashboard in another terminal, and open http://localhost:3000 full screen:
   ```powershell
   cd apps/web; pnpm exec next start
   ```

**The newer dashboard, `apps/web-combined`, has only run on the CPU stack.** Use `apps/web` above for the GPU demo until a GPU run passes on it. The CPU fallback below always uses `apps/web-combined`.

## The demo (about 4 minutes)

| Do | Say |
|---|---|
| Show the screen before any job | "One real GPU here. The badges tell you which providers are real, capped, or faulty on purpose." |
| In a terminal: `.\.venv\Scripts\python.exe experiments\start_demo_job.py` | "The budget is locked on-chain, along with the quality terms, before a single step runs." |
| Point at the headline and loss chart | "Provider A was chosen on measured speed and price." |
| **Ask a judge to press Kill Provider A, twice** | "That really kills the process. No warning." |
| Headline changes in under a second | "Detected. The old worker can no longer write anything." |
| Provider P takes over | "P is the cheapest replacement. It's cheating, and we've labelled it. Watch: it reports normal progress." |
| The hatched branch drops off the line | "Independent verifiers rejected it. It reported success, and the evaluation disagreed. It earns nothing." |
| Point at the provider list | "C can't fit this job, so it was refused with a measured reason. B fits if it changes how it batches, so the same logical batch runs as 8 × 4." |
| Payout table and transactions | "Paid on-chain only for accepted work: A and B by steps, nothing for P, and the rest back to the client." |
| On `apps/web-combined` only: press **Verify** by the payout, then **Run the checks** | "Don't trust our screen. Your browser reads the verdict from the chain and works out the payout again." |
| Show the limits | "Our verifiers are permissioned, this GPU is shared, and the contract is unaudited. Here's what we measured, and what we can't claim." |

**Timing note:** with the current 400-step job, A reaches step 150 about 15 seconds after training starts, so have the judge ready. From a kill to the payout took about 160 to 200 seconds in testing.

## If something goes wrong

| Problem | Do this | Say |
|---|---|---|
| Testnet is down | Use the local chain (the default) | "This is a local test chain." The dashboard shows a badge |
| GPU fails or overheats | `.cache\cpu-venv\Scripts\python.exe experiments\demo_stack.py --cpu --no-docker --total-steps 6000`. In `apps/web-combined`: `npx next start -p 3100`. Open http://127.0.0.1:3100/?view=dashboard, press **Start demo job**, then **Kill**. No GPU or Docker. Set up once beforehand with `bash infra/setup-host.sh`, and build the dashboard. It shows no memory adaptation. **Needs about 3.5 GB free, so close other apps first** | "This is the synthetic CPU fallback." |
| Laptop or stack fails | In `apps/web`: open http://localhost:3000/?mode=replay. In `apps/web-combined`: open http://127.0.0.1:3100/?at=0&play=4. Or play the backup video | "This is a recording of a real run." The dashboard shows a badge |
| Run stops from low memory | Close more apps, and restart the stack | |

**Always say out loud when you're using a fallback.**

## Rehearsing without the dashboard

With a stack running, `python experiments/rehearse.py --rounds 8` runs job after job and checks each payout on-chain. It finds flaky bugs, and doesn't replace the 10 rehearsals by people.

## Second GPU

See `docs/second-gpu-provider.md`. Test it days before the demo, not on the day.

## Security on the day

Run **one coordinator only**. Two at once could both start the same job (Arvind, 7 Nov). Before a testnet run, set one fixed RPC address in `.env`, and check that its chain ID is 84532.

The operator API only answers this laptop. For a hotspot or second GPU, set `API_TOKEN` in `.env` first. See `docs/security-and-privacy.md`.

**Payout verification remains under validation:** default secure verifiers check signed payout evidence independently; the explicitly unsafe local demo mode still trusts the coordinator's proposed split. Do not claim the complete payout protocol is secure until the required end-to-end and adversarial checks pass. The Verify page uses coordinator-supplied checkpoint and provider details; configure the expected escrow address independently. See `docs/payout-verification-design.md` and `docs/signed-payout-setup.md`.

## Never claim

First decentralized GPU network. Zero downtime. Trustless compute. Works on any GPU. Proven training equivalence. Faster than a named competitor.

## Numbers you can use

Only from `experiments/results/` and `experiments/G1_RESULTS.md`. Say how many runs each one comes from. For competitor questions, use `docs/market-gaps.md`.
