# Hard questions judges may ask, and honest answers

Written 7 Nov 2026. Each answer says what backs it. If an answer stops being true, change it here before the demo. Never stretch an answer past its evidence.

## Why this, and why blockchain?

**"Isn't this just a GPU marketplace with a token?"**
No token, and we're far smaller than Akash, io.net or Vast. What's different is the combination: the job moves when a provider dies, a quality test agreed before training decides what counts, and escrow pays only for accepted work. We didn't find the three together in what we read. Source: `docs/market-gaps.md`.

**"Why does this need a chain? A database could do it."**
A client and a provider who don't trust each other need the money held somewhere neither controls. The chain holds the budget before work starts, and fixes the quality terms by hash. It pays out only on a 2-of-3 verifier signature, and lets anyone take the timeout refund if our servers vanish. The chain doesn't make the compute itself trustworthy: the quality test does that.

**"Who are your verifiers?"**
Our own team runs all three, so it's permissioned, not trustless. Two colluding verifiers could approve bad work. Independent verifiers come next.

## Does it really work?

**"Was that a real GPU?"**
Yes, one RTX 3060 Laptop, on 4 and 5 Nov. Providers B and C were memory caps on the same card, labelled as such. One run and one seed per result, on a local chain. Sources: `experiments/results/recording_job_4f605443_20261104/`, and `gpu_chain_story_20261105_001829.json`.

**"Does it work across different GPUs?"**
Not shown yet. Vaibhav trained a start leg on a Kaggle Tesla T4, and the checkpoint loads in our code. Resuming it on the 3060 hasn't been done. Source: `experiments/results/external_vaibhav_t4_20261106/`.

**"Does recovery hurt the model?"**
On one T4, 5 seeds, 2,000 examples: no degradation detected beyond 2 accuracy points, with a mean change of +0.09 points. That's the same GPU, resuming from a saved checkpoint, with no real kill. Same source.

**"How fast is recovery?"**
In the recorded run: 0.6 s to notice, 65 s until training resumed elsewhere, 41 s of that spent checking the checkpoint first. 8 of 400 steps were lost.

**"Is this live, or a recording?"**
Say which, every time. The dashboard shows a RECORDED badge for recordings, and SYNTHETIC for the CPU fallback.

## Money

**"Who got paid, and why?"**
A earned 0.15 test USDC for 150 accepted steps at 0.001. B earned 0.75 for 250 at 0.003. P earned 0, because its work was refused. 4.10 went back to the client, out of a 5 USDC budget. The Verify page re-checks the payout against the chain. The Settlement page downloads an itemised receipt.

**"Is this real money?"**
No. Test USDC on a local chain. Base Sepolia, a public testnet, is the next step, and it hasn't run yet.

**"What if the job fails at the very end?"**
Honest providers can go unpaid. The contract permits a failed verdict to refund the client in full, but the default secure verifier does not yet sign failed-job verdicts. An eligible client can use the timeout refund after the deadline and grace period, then withdraw the credited funds. Paying accepted work on a failed job up to an agreed cap needs a contract change and a reviewed signing path. Source: `docs/payment-incentives-analysis.md`, attack 2.

**"Is the contract audited?"**
No. 85 tests pass, Arvind reviewed it as an attacker, and Slither reported no High or Medium findings, by their report. Testnet only.

## Security and privacy

**"Can a provider see my data?"**
Yes. There's no secure hardware enclave on these GPUs, and checkpoints aren't encrypted. Use public data only. We don't claim private training.

**"Can a provider fake its results?"**
It can report anything, but payment depends on the verifiers' own evaluation, not on what the provider reports. A provider can also train on our public test set, which the evaluation can't catch. The fix is a test set the client keeps private.

**"What stops someone on the network from controlling the job?"**
The operator API only answers this laptop, or a holder of the token. Agents and verifiers sign what they send. Source: `docs/security-and-privacy.md`.

## Never say

First, only, trustless, zero downtime, works on any GPU, proven equivalence, private training, audited, regulated, compliant.
