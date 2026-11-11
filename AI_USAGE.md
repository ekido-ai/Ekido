# AI usage — GPUChain

How an AI coding assistant was used to build this project.

## Division of work

- **The team** set the goal, the scope and every product decision: what to build, which trade-offs to accept, the 8% fee, the design direction, what to deploy and when. Teammates ran the cross-GPU and probation experiments on their own machines, reviewed the contracts as attackers, and shaped the UI.
- **The assistant** drafted plans, most of the code, the tests and the docs, proposed options with reasons for the team to accept or reject, ran and verified the work, and deployed to the test network only after explicit approval.
- Keys stayed in gitignored environment files. They were never printed, hardcoded or committed.

## How results were kept honest

- Every number in the README, the docs and the pitch traces to a raw file in `experiments/results/` or to an on-chain transaction.
- CPU and synthetic runs are labelled as such and never presented as GPU evidence.
- Claims the evidence doesn't support were refused, even when they would have made the pitch stronger: "trustless", "any GPU", "zero downtime", "proven equivalence" and "private training".
- When a claim turned out to be wrong, such as a slide saying a service came back on its own after a restart when it hadn't, it was corrected before shipping.
- "It works" was said only after running it; anything not run was stated plainly.

## What the authors must be able to explain

- Why a logical training step means the same thing on any GPU, and what changes between GPUs.
- How the quality test decides pass or fail, and why the margin and evaluation set are fixed before training.
- Why the escrow's payout rule, quorum, dispute window and timeout refund protect each side.
- What the coordinator can and cannot do with money.
- What the prototype does **not** guarantee (see the Limitations section of the README).
