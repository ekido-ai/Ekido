# Real probation-noise run: Kaggle T4, 7 Nov 2026

Everything below is read directly from `probation_noise_real_20261107_074433.json`, `environment.json` and `probation_run.log` in this folder. All three match `SHA256SUMS.json`. Original download: `GPUChain_probation_outputs_2026-11-07.zip`, SHA-256 `130054ab605dbd8499e074ff210cd78a5241f1754ee9810d360ef05cc4e36f7a`.

## What was run

- Command: `python experiments/probation_noise.py --real --device cuda --seeds 5 --eval-examples 2000 --identity experiments/results/identity_agnews_20261107.json` (exit code 0, about 1,730 s for 5 seeds)
- Machine: Kaggle, Tesla T4 (14,911 MiB usable, compute capability 7.5), driver 580.178.04, CUDA runtime 13.0. The session showed two T4 entries in `nvidia-smi`; the run used `cuda` device 0.
- Software: Python 3.13.16, torch 2.11.0+cu130, transformers 5.20.2, peft 0.21.2, datasets 4.8.5, safetensors 0.8.0, accelerate 1.15.0, numpy 2.1.3.
- Pinned identity: model `distilbert-base-uncased` @ `12040accade4e8a0f71eabdb258fecc2e7e948be`; dataset `fancyzhx/ag_news` @ `eb185aade064a813bc0b7f42de02595523103ca4`; train SHA-256 `65011f77...a0e5` (120,000 rows); test SHA-256 `510142e2...e092` (7,600 rows). The bundle's 47 files matched their expected hashes before the run.
- Workload: real DistilBERT LoRA on AG News, 400 logical steps per seed, checkpoint every 25 steps, 2,000 evaluation examples (eval-set hash `efd9f992...8e9d`).

## Result

Each checkpoint was evaluated against the one before it (15 pairs per seed, 75 pairs over 5 seeds). Honest runs only.

| Margin | Pairs refused | Seeds with any refusal |
|---|---|---|
| 0.02 | 0 of 75 | 0 of 5 |
| 0.03 | 0 of 75 | 0 of 5 |
| 0.05 | 0 of 75 | 0 of 5 |
| 0.08 / 0.10 / 0.15 | 0 of 75 | 0 of 5 |

- Worst pair: seed 4, step 275 to 300, accuracy 0.9035 to 0.8930, difference -0.0105, one-sided CI lower bound **-0.0165**.
- Across all 75 pairs: difference min -0.0105, mean +0.0053, max +0.0735. CI lower bound min -0.0165, mean -0.0008.
- The current mid-training margin of 0.05 has about 3.4 points of room over the worst observed lower bound (-1.65 points). Even 0.02 refused nothing in this sample.

## What this does and does not show

- It shows: on this T4, with these 5 seeds and 2,000 evaluation examples, no honest checkpoint pair was refused at margin 0.05 (or at any margin tested).
- It does not show: that 0.05 is right for other seeds, other GPUs, longer jobs or other eval sets. Five seeds is a small sample.
- It says nothing about detecting bad providers: only honest runs were trained, so it is not a false-negative test.
- It is not cross-GPU evidence, not a process-kill test, and not a result from the demo laptop. Same device, one T4.
- Two T4 entries appeared in `nvidia-smi`; only one was used by the run.

## Open items (unchanged)

Cross-GPU leg on the RTX 3060 and the T4 return leg, teammates' GPU inventory, demo heat/timing, and the torch-dependent test files (5 verifier, 3 runtime) are still not run.

## Note on the earlier failures

The first notebook runs failed for setup reasons (no GPU selected; dataset layout). One run then exited with code 5 on seed 1 with no traceback in the log. The final run passed with the same bundle and command. I do not know why that earlier run failed, so I am not claiming a cause.
