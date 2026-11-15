# The market problem Ekido targets

Research done on 9 Nov 2026. Most sources are vendor blogs, docs and preprints, so treat their numbers as indicative, not measured by us. Our own numbers stay in `experiments/results/`.

## Renting spare GPUs

| Problem | Evidence | What Ekido does |
|---|---|---|
| Hosts drop out mid-run, and resuming is the user's job | ClusterBid on Vast.ai: hosts "can be terminated at any time"; consumer sessions often last hours; workloads must be "designed for interruption tolerance" | Automatic recovery from the last accepted checkpoint, onto a different GPU if needed (`/recovery`) |
| Billing is by time, not by outcome | RunPod bills every 5 minutes; Vast.ai: no refunds once credits are spent; no published rule for a host failing mid-job | Budget locked in escrow; pay per accepted step; the rest refunded (`/settlement`, `/chain`) |
| Nobody checks the work | Exact recomputation fails across GPUs (arXiv 2501.05374); "lazy worker" results; reputation stands in for verification | Paired-bootstrap Quality Guard agreed before the job; refused work earns nothing (`/quality`) |
| Failures waste real compute even at big labs | Llama 3: 466 job interruptions in 54 days; failures touched 19% of GPU runtime in one cluster (arXiv 2410.21680) | Same problem, worse on consumer hosts: this is the job we make survivable |

## Paying for compute on a blockchain

| Problem | Evidence | What Ekido does |
|---|---|---|
| Providers paid in a volatile native token | Aethir launched a USD stablecoin because volatility "deters long-term participation" | USDC only. No Ekido token |
| Emissions reward existing, not working: fake nodes, demand far behind supply | Tokenomics guides on flat per-node rewards; Akash about $2M fees, Render about $1.9M job spend in a year | Nothing minted. Payouts come only from client budgets for accepted work, so a fake node earns zero |
| The chain can't see off-chain work (oracle problem) | Cointelegraph op-ed: corrupted Render jobs in 2025, "no onchain way to detect it" | 2-of-3 EIP-712 verifier quorum over the result hash, lineage root on-chain, dispute window with a bond. Verifiers are team-run: permissioned, and we say so |
| Funds depend on the operator staying alive | General escrow risk | `claimTimeoutRefund` is permissionless after deadline + grace |
| Balances are the platform's word | General | Live proof of reserves and a double-entry journal rebuilt from chain events (`/chain`) |

## The one-line positioning

Pay for accepted results, not GPU-hours: the job survives a dead GPU, junk is refused before it's paid, and the money is in USDC under rules anyone can check on-chain.

## Sources

- ClusterBid, Vast.ai deep dive: https://clusterbid.com/blog/vast-ai-gpu-marketplace-deep-dive-decentralized-pricing-reliability
- Vast.ai billing docs: https://docs.vast.ai/documentation/reference/billing
- RunPod billing docs: https://docs.runpod.io/accounts-billing/billing
- Validation of GPU Computation in Decentralized, Trustless Networks: https://arxiv.org/pdf/2501.05374
- Revisiting Reliability in Large-Scale ML Research Clusters: https://arxiv.org/pdf/2410.21680
- TrainMover: https://arxiv.org/pdf/2412.12636
- Aethir AUSD: https://aethir.com/blog-posts/aethir-and-maitrix-launch-ausd-stability-for-decentralized-gpu-infrastructure
- DePIN tokenomics guide: https://www.tokenomics.net/guides/depin-tokenomics/
- "Decentralized compute has failed, so far" (Cointelegraph, opinion): https://www.tradingview.com/news/cointelegraph:d08daf58e094b:0-decentralized-compute-has-failed-so-far/
- Ocean Network USDC escrow on Base: https://decrypt.co/364596/ocean-network-builds-airbnb-for-compute-network-using-idle-gpus
