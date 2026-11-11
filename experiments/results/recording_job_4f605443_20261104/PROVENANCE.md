# Recording of GPU job 4f605443 (4 Nov 2026)

`replay.json` is the event log of a real run on the RTX 3060 with a local Anvil chain, saved by `experiments/make_replay.py` from the running stack. Every event is marked RECORDED. It's a byte-for-byte copy of `apps/web/public/replay.json` and `apps/web-combined/replay/recordings/real-run.json` (SHA-256 starts `cefeba2528ed`). `real-run-2026-11-04.json` is the same events, with a budget note added.

The landing page's numbers come from this run, and are derived from its events:

| Number | From |
|---|---|
| 0.6 s to notice | `fault.injected` to `failure.detected`: 0.62 s |
| 65 s until training again | `fault.injected` to `recovery.step` RESUMED: 65.2 s |
| 41 s checking the checkpoint | `fault.injected` to SELECT_CHECKPOINT, after the handover evaluation: 41.2 s |
| 8 steps lost | `recovery.step` `lost_steps` |
| 24.8% junk, 89.2% before, 90.7% final | `quality.result` accuracies |
| A 0.15, B 0.75, refund 4.10 USDC | Not recorded as amounts. Derived: accepted checkpoints at steps 150 (A), then 200 and 400 (B). That's 150 steps at 0.001 and 250 at 0.003, from the stack's provider prices, against a 5 USDC budget. The same amounts were recorded on-chain in the three other story runs in this folder |

One run, one seed, local chain, one physical GPU with memory caps. This raw folder has no other copy of the run.
