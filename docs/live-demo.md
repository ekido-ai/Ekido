# Showing the live network

For when someone says "show it live". The live network is https://gpuchain.duckdns.org: a coordinator on Base Sepolia with test USDC, two CPU providers (one on Google Cloud, one on AWS) and the dashboard. For the recorded story and the CPU fallback on a laptop, see `demo-runbook.md`.

## What this can and cannot show

- It shows: a job funded in the escrow, two providers online, one provider stopped mid-run, the job moving to the other from its last accepted checkpoint, the payout settling on chain, and `/verify` recomputing it in the browser.
- The providers are **CPUs running the synthetic workload**. Say so. It is not a GPU result.
- A full kill during a funded job has **not been rehearsed on this network yet**. What has been measured: with no job running, stopping the AWS provider showed it OFFLINE on the live coordinator within 5 seconds, and starting it showed ONLINE again within 6 seconds. Do one complete dry run with a small budget before the real one.

## Ten minutes before

```bash
python infra/live_preflight.py
```

It must end with `ready to show`. It checks the coordinator, two or more providers online, the pages, the certificate and the escrow contract. It only reads. If you have more friends connected, `--min-providers 3` and so on.

Have ready:
- A browser wallet on **Base Sepolia** with a little test ETH for gas and enough test USDC for the budget. A 400-step job at 0.001 USDC a step is 0.4 USDC plus the 8% fee.
- The SSH details for the AWS instance, and `gcloud` access to the Google Cloud VM, if you want to stop that provider instead.
- The recorded run (`/replay`) open in another tab as a fallback.

## The sequence

1. Open `/dashboard` and show the two providers online.
2. Open `/jobs/new`, connect the wallet, sign the job terms and fund the escrow. The funding step walks through switching to the right network, allowing the escrow to take exactly the budget, and locking it. Every signature happens in the wallet.
3. Watch the job start on one provider.
4. Stop that provider.
   - AWS: `ssh -i <key> ubuntu@13.236.178.101 "sudo systemctl stop gpuchain-aws-provider"`
   - Google Cloud: `sudo systemctl stop gpuchain-sepolia-smoke-provider` on the VM.
5. The dashboard shows the failure detected, and the other provider taking over from the last accepted checkpoint.
6. When the job settles, open `/settlement` for the receipt and `/verify` to recompute the payout from the chain.
7. Start the stopped provider again:
   - AWS: `ssh -i <key> ubuntu@13.236.178.101 "sudo systemctl start gpuchain-aws-provider"`

## If something goes wrong

| Problem | What to do |
|---|---|
| Preflight fails | Do not start. Read which check failed. A provider offline is usually a stopped service: start it as in step 7. |
| Wallet is on the wrong network | Use the "Switch to" step on the funding page, or switch to Base Sepolia in the wallet. |
| The job does not start | Check `/sepolia/readyz`. Look at `coordinator_gas` (it needs test ETH) and `settlement_backlog`. |
| Both providers go down | Start them, then fall back to `/replay` and say it is a recording. |
| Anything unexpected | Say what it is. The recording and the raw results in `experiments/results/` are the evidence. |

## Say it honestly

Test network, test USDC, unaudited contracts, verifiers run by the team, CPU providers, public data only. The recorded GPU run and its raw files are in the README.
