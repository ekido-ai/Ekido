# Payment incentives: how a provider could game GPUChain

Written 7 Nov 2026. It covers the payment rule as built: payout = accepted steps x price, capped at the budget, after a 2-of-3 verifier verdict. The contract supports a full client refund on a failed verdict, but default secure verifiers do not yet sign failed-job verdicts. The separate eligible timeout refund opens after the deadline and grace period, and credited funds must then be withdrawn. This is reasoning about the design, not a test result.

## The rule, in one line

You earn only for steps that end up in the accepted model's checkpoint lineage, at your declared price, and only if the job as a whole passes.

## Attacks, and who pays for them

| # | Attack | What happens today | Who loses | Fix, and whether it needs a contract change |
|---|---|---|---|---|
| 1 | **Junk work**, like poisoned weights or skipped training, reported as normal | Verifiers refuse the checkpoint. The provider is fenced off and earns 0 | Only the attacker's time. **The rule works here**: shown live with P at 24.8% | — |
| 2 | **A spoiler at the end.** Train honestly, or not at all, as the last replacement, then hand in a bad final model when no other provider is left | The job fails and honest providers may earn nothing. A failed-verdict full refund is supported by the contract but not signed by the default secure workers; an eligible timeout refund is available after the deadline and grace period | Honest providers who did accepted work; the client may wait for a refund | Pay accepted lineage on failure with a cap: that needs a contract change and reviewed signing. For the demo, keep a spare honest provider and disclose the limit |
| 3 | **Subtle damage below the margin.** Lower quality by less than the margin at each check | The mid-training margin is 0.05 and the final is 0.02. Small, repeated damage can pass mid-training, but the final check and its absolute floor bound it | The client gets a slightly worse model | Bounded, not prevented. Disclosed in `docs/market-gaps.md` |
| 4 | **Training on the public test set**, so evaluation looks better than the real model | It would pass. The evaluation set is public | The client | Needs a private holdout set held by the client. Disclosed |
| 5 | **Price manipulation.** Bid low to win the job, then fail early | You're paid only for accepted steps, so failing early earns little. The scheduler counts past failures | The client loses time, not money | Partly covered. Staking would make it costly. Future work |
| 6 | **Many identities.** Come back as a "new" provider after being caught | Providers are registered by the operator, so a stranger can't self-register today | — | Becomes real with open sign-up. That would need stake or a reputation that costs something |
| 7 | **Delay.** Hold the job without making progress | The lease and watchdog mark the provider failed, and the job moves on. Unsaved steps earn 0 | A little of the client's time | Covered |
| 8 | **The client refuses to pay** | The budget is locked in escrow before any step runs. The client can only dispute, with a bond | — | Covered by escrow. Disputes go to one team arbiter, which is disclosed |
| 9 | **Colluding verifiers**, 2 of 3, approve junk | They could. The team runs all three | Client and honest providers | Needs independent verifiers. Disclosed |
| 10 | **The coordinator lies about the payout** | Secure verifiers check signed evidence and configured chain facts. The Verify page also checks consistency, but relies on coordinator-supplied checkpoint and provider metadata | Potentially client or providers if trust assumptions fail | Disclose both limits; the browser check alone does not authenticate all inputs |

## What to say to judges

- **Strongest point:** "Bad work isn't just caught, it isn't paid. The payment is tied to the same test that rejected it, so cheating earns nothing."
- **Admit attack 2 before they find it:** "Today, a final failure can leave honest providers unpaid. Secure failed-job signing is not implemented; an eligible client can claim a timeout refund after the deadline and grace period. Paying accepted work on failure is a proposed contract change, not a built feature."
- **On trust:** "The escrow and the payout rule are on-chain. The verifiers aren't independent yet: our team runs them."

## The fix for attack 2, as a design (not built)

- The verdict can carry payouts even when `passed` is false. Accepted lineage steps are paid at their price, but only up to a cap. The cap could be a fraction of the budget agreed in the policy before the job runs, so a client isn't forced to pay in full for a model it didn't get.
- The policy hash already fixes terms before training, so the cap belongs in the policy.
- The contract's `passed=false` rule (full refund, no payees) has to change. It's the money path, so it needs Arvind's review, after the demo.
