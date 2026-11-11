# Review of `contracts/src/GPUChainEscrow.sol` (Piyush's version)

Reviewer: Arvind, 5 Nov 2026, with Claude. **Unaudited, not a professional audit.** Local only, nothing deployed to a public network.

## What I ran (real results)
| Check | Result |
|---|---|
| Your suite, `forge test --offline` (Foundry 1.9.0, solc 0.8.28, OZ 5.7.0) | **61 passed, 0 failed** |
| My attacker tests, `contracts/test/AttackerReview.t.sol` (new file, nothing of yours changed) | **23 passed: 6 weaknesses reproduced (`poc`), 17 defences hold (`holds`)** |
| Slither 0.11.6, escrow | 10 results, **0 High/Medium**, all dismissed (see below) |
| Slither 0.11.6, registry | 1 result (unindexed event address), dismissed |
| Anvil fallback: `Deploy.s.sol` on local Anvil (chain 31337) | Deployed MockUSDC, Escrow, Registry. `cast` read back coordinator, arbiter, bond = 1000000, verifier set = 1, quorum = 2 |

Not done: invariant/fuzz of my own on your contract (yours has 1 invariant test and 2 fuzz tests), BaseScan verification, Base Sepolia deployment, funding. A passing `holds_*` test that uses a bare `expectRevert()` proves "it reverts", not why.

## Findings (each has a passing `test_poc_F<n>_...`)
| ID | Severity | Finding | Suggested fix |
|---|---|---|---|
| F1 | **Medium** | The client picks `deadline`. A refund opens at `deadline + 1h` even if the job is still running. If the verdict is signed but not submitted yet, the client calls `claimTimeoutRefund` first and every provider gets 0. The valid quorum then fails with `WrongState(Refunded)`. | No contract change needed for the demo: coordinator checks the on-chain `deadline` matches the spec before `markActive`, and submits the attestation well before `deadline + 1h`. Disclose it. |
| F2 | **Medium** | `setArbiter` works mid-dispute. A new arbiter can pick the split among the verdict's payees (A gets everything, B and the client get 0) and take the bond. Verifier set is snapshotted, arbiter is not. | Store `arbiter` in the `Job` at `createJob` and check `job.arbiter` in `resolveDispute`. About 3 lines + 1 test. |
| F3 | **Medium** (griefing) | A dispute costs the client nothing if the arbiter is silent: the bond comes back. Any client can delay all provider payouts by 3 days for free. | Decision for the team. Cheapest: disclose (bounded to 3 days). Alternative: forfeit the bond on timeout. |
| F4 | **Medium-Low** | Job IDs are global. An attacker who sees a pending `createJob` can take the same ID for 1 unit and cancel. The ID is then burned for the real client. Attacker pays only gas. | Derive `jobId` from the client address (coordinator side) and check it on-chain, or disclose. |
| F5 | **Low** | `markActive` does not check the deadline. A job can be activated after it expired. | Add `if (block.timestamp >= job.deadline) revert BadDeadline();` in `markActive`. |
| F6 | **Low** | `setCoordinator`, `setArbiter`, `setVerifiers` are one key (owner), instant, no delay. No existing test calls `setArbiter` or `setCoordinator`. | Disclose: single deployer key is the admin. My `poc_F6` pins today's behaviour. |

Not a finding but worth fixing: `Deploy.s.sol` reads the **private keys** of coordinator, arbiter and all 3 verifiers. It only needs their **addresses** (`vm.envAddress`). That way only the deployer key is needed on the deploy machine.

## Slither results and why dismissed
- `uninitialized-local` (`previous` in `_checkSignatures`, `paid` in `_applyVerdict`): intended, default value 0 is the starting value.
- `timestamp` (6 comparisons): deadlines and windows are in hours and days. A validator can shift a timestamp by seconds only. Not exploitable. (F1 is a design problem, not a timestamp problem.)
- `unindexed-event-address` (`CoordinatorUpdated`, `ArbiterUpdated`, registry `CoordinatorUpdated`): cosmetic. Optional: add `indexed`.

## What held up (tested)
Signature replay on another job, another chain, another deployment. Same verdict twice. One verifier counted twice. Malleable high-s copy. Non-verifier signers. One signature is not a quorum. Changing payees or amounts after signing. Amounts that do not sum to the budget even with valid signatures. Expired verdict. Strangers cannot dispute, resolve, activate, anchor or call owner functions. Dispute twice or after the window. The arbiter cannot add payees or pay more than the budget. Withdraw twice. A blacklisted payee cannot block anyone else (pull payments). The coordinator can delay a cancel but not steal, and a stranger can trigger the timeout refund without it.

## Your five decisions
1. **Admin-managed verifier set, snapshotted per job:** works as stated (tested by yours). Gap: the arbiter and coordinator are not snapshotted (F2, F6). A compromised old verifier cannot be removed from a running job, as you noted.
2. **Failed job = full refund:** confirmed in code (`FailedVerdictHasPayees`). Harsh for honest providers when a good model is refused once. Changing it touches the `Verdict` rules, Python signing and vectors: ask before doing it.
3. **Bond 1 USDC, grace 1h, window max 7d, arbiter timeout 3d:** match the code. Bond is constructor-fixed, the rest are constants. They are demo values, not measured.
4. **`anchorEvent`:** coordinator only, Active jobs only, event only. Spam costs the coordinator gas, moves no money. Fine.
5. **Deadline refund after work is done:** this is F1.

## Not changed
Your `contracts/` was not touched. The only new file is `contracts/test/AttackerReview.t.sol`. Verdict struct, EIP-712 and events are unchanged.
