# Vaibhav's real-model probation run (7 Nov 2026)

Copied, without running any code, from `C:\Users\Mahak\Downloads\attachments.zip` (SHA-256 `9e797f3ef62a69e9445fec5bbe1d9ce6cd110a0e352c1a3b6123f77caa2079c8`). The three files listed in `SHA256SUMS.json` matched their hashes when copied.

**What it shows:** on one Kaggle Tesla T4, real DistilBERT LoRA on AG News with a pinned model and dataset revision, 5 seeds, 75 consecutive honest checkpoint pairs, 2,000 evaluation examples, no pair was refused at any margin from 0.02 to 0.15. The worst lower bound was -0.0165 (seed 4, step 275 to 300). That supports the 0.05 `probation_margin` in the demo policy.

**What it doesn't show:** a cheating provider being caught, behaviour across GPUs, or a real process kill. The hardware is as reported by the file, not independently verified. Vaibhav also reports one earlier attempt that exited with code 5 on seed 1, with no traceback, before this run passed. The cause is unknown.
