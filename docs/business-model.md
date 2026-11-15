# Business model and pricing

Draft, 9 Nov 2026. Market figures are third-party snapshots that move daily; our own measurements live in `experiments/results/`. Nothing here is charged yet: the test network takes no fee.

## 1. Who pays whom

| Party | Pays | Gets |
|---|---|---|
| Client (trains a model) | Provider price × accepted steps, plus our fee on that amount | A finished model that passed the agreed quality test; full refund if the job fails |
| Provider (rents out a GPU) | Nothing to join; gas to list on-chain (cents) | Its own price × its accepted steps, in USDC, withdrawn whenever it likes |
| Verifiers | Their own compute | A share of the fee (planned), so independent verifiers can exist |
| Ekido | Coordinator infrastructure, gas for settlement, development | The rest of the fee |

## 2. What the market charges (one GPU, per hour)

| GPU | Typical marketplace rate | Source |
|---|---|---|
| RTX 4090 | $0.34 to $0.69, median about $0.55 | RunPod Community, Vast.ai, Oct 2026 |
| A100 80 GB | $0.40 to $1.19 | Vast.ai, RunPod, Oct 2026 |
| H100 80 GB | $1.50 to $2.99 | Vast.ai, RunPod, Oct 2026 |
| RTX 3060 | No published figure found | We use about $0.10 as our own estimate and label it so |

Take rates seen: Vast.ai says hosts keep the full rate they set and renters pay no markup (it earns on other charges). Paralon publishes a 20% platform fee. RunPod and Akash rates weren't found.

## 3. Our pricing, and why it lands slightly cheaper

- **Providers set an hourly rate.** The site converts it to a price per accepted step using the provider's speed, because payment is per accepted step. It suggests about 15% under the market rate for that GPU class.
- **Proposed fee: 8% of accepted work, paid by the client on top.** The provider keeps 100% of its price, as on Vast.ai.
- **Result:** the client's hourly cost is about 0.85 × 1.08 = **0.92 of the market rate**, so slightly cheaper, not a race to the bottom.
- **The bigger saving is structural:** the client pays nothing for time lost to a dead GPU, for work that fails the quality test, or for a job that fails outright (full refund, no fee). On a marketplace billed by the minute, all of that is paid for.
- **Not too cheap:** providers earn close to the market rate, so they have a reason to stay. The fee is charged only on success, so our income depends on jobs actually finishing.

## 4. How we make money

1. **Protocol fee, 8% of accepted work.** Charged only when a job settles successfully. No fee on refunds. This is the core revenue and scales with volume.
2. **Planned split of that fee:** 3% to the verifiers who signed the verdict, 5% to Ekido. Paying verifiers is what lets independent operators run them, which is the main step toward a decentralized verifier set.
3. **Later, priced separately, only after the core works:**
   - Private verification: a client's own hidden evaluation set and verifier set.
   - Guaranteed finish: a higher price that funds standby providers for jobs with hard deadlines.
   - Confidential training on hardware with TEE attestation.

There is **no token**: no emissions to subsidise supply, no treasury to sell. Revenue is fee × the volume of accepted work, from day one.

## 5. Unit economics, per job

Costs that grow with each job:
- **Gas:** our one real settlement used about 572k gas in total across funding, activation, attestation and finalization. Base fees are low, but this must be measured on mainnet before setting a minimum fee.
- **Verification:** each verifier evaluates checkpoints on its own hardware. The 4 Nov run's evaluation set was 2,000 examples.
- **Coordinator:** small per job; mostly fixed cost.

Because fixed costs per job exist, a **minimum fee per job** will be needed once gas and verification are measured on mainnet. We won't set its value until then.

## 6. To decide

- The fee rate (8% proposed) and the verifier share (3% proposed).
- The minimum fee per job, after mainnet measurements.
- Whether the fee is a separate payee in the on-chain split. The escrow already allows up to 8 payees, so this needs no contract change: the coordinator adds a fee payee to the verdict, the verifiers sign it, and anyone can see it on the On-chain page. It must also be part of the job's signed terms before funding.

## Sources

- https://joulemath.com/blog/gpu-rental-prices-h100-h200-a100-rtx-4090-october-2026/
- https://dev.to/lanternworks/gpu-rental-prices-compared-h100-a100-rtx-4090-and-more-oct-2026-eha
- https://www.spheron.network/blog/runpod-vs-vastai-2026/
- https://vast.ai/hosting
- https://paraloncloud.com/resources/paralon-vs-vast-ai-for-hosts
