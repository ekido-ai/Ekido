# Vaibhav Parmar — GPUChain evidence and work, 5 Nov 2026

Base for all of this: `GPUChain_Team_Pack_2026-11-05.zip` (the final pack from
Piyush's mail of 5 Nov). No git commits or pushes were made, per the team rule.
Work was done on Kaggle (account vaibhavparmar7002) and on a Linux VM with no
GPU. Nothing here was run on the demo laptop.

## 1. Pack verification (Linux, CPU)

The pack was unpacked and Vaibhav's areas were re-run against it:

```
packages/gpuchain_core:  python -m unittest discover -s tests  -> 126 tests, OK
workers/runtime:         python -m unittest discover -s tests  ->  47 tests, OK
```

Both match HANDOFF.md exactly. The merged items from my earlier repo review
(`docs/vaibhav-repo-review-2026-11-05.md`, already in the pack) were confirmed
present in the pack's code: the compiler probe-budget fix in
`packages/gpuchain_core/gpuchain_core/compiler.py`, the `CANARY_MISMATCH` error
code and the real `driver_version()` in `workers/runtime/gpuchain_runtime/run.py`,
and the `CORRUPT_CHECKPOINT` expectation in `experiments/fault_matrix.py`.

## 2. Cross-GPU test, leg 1 of 3 — DONE on a real second GPU

Machine: Kaggle, Tesla T4 (compute capability 7.5, 14,911 MiB), torch
2.11.0+cu130, CUDA 13.0. Notebook:
https://www.kaggle.com/code/vaibhavparmar7002/notebook4ee5bf3997

Exact command (repo root, pack unpacked, `transformers==5.22.1`,
`peft==0.21.2`, `safetensors`, `datasets`, `numpy`, `eth-account` installed):

```
python experiments/cross_gpu_resume.py start --out handover_t4 --steps 150 --device cuda
```

Result (`experiments/results/cross_gpu_leg1_t4/evidence.json`):

- evidence_type: REAL GPU RUN; steps 0 -> 150; precision FP16 (chosen by the
  repo's own rule for CC 7.5); micro-batch 16 x accumulation 2
- **accuracy after the leg: 0.896 on 2,000 evaluation examples**
- 49.3 s of training; peak memory 687.8 MiB
- The checkpoint was downloaded and re-validated locally with the pack's own
  `load_checkpoint`: valid GPCK/1, manifest step 150, environment "Tesla T4".

The full checkpoint folder is in `handover_t4/` in this zip **for Vaibhav
only** — per the mail rules, checkpoint tensors are not sent to Piyush; the
submission copy keeps only `evidence.json`, `manifest.json` and `spec.json`
(under `experiments/results/cross_gpu_leg1_t4/`).

Still to run (the checkpoint starts on the T4 because that is the GPU
available tonight; any T4 <-> 3060 alternation is the cross-GPU proof):

```
# Leg 2, on the RTX 3060 (about 2-3 minutes; ask Piyush before using the demo laptop):
python experiments/cross_gpu_resume.py resume --checkpoint handover_t4 --out from_other_gpu --steps 50 --micro-batch 8

# Leg 3, back on the T4 (Kaggle, infra/cross_gpu_notebook.ipynb pattern, micro-batch 16):
python experiments/cross_gpu_resume.py resume --checkpoint from_other_gpu --out back_home --steps 50 --micro-batch 16
```

## 3. Quality comparison (5 seeds) — DONE on Tesla T4

Official script, committed on Kaggle as a server-side run on a Tesla T4:
https://www.kaggle.com/code/vaibhavparmar7002/notebook90e4017165
(scriptVersionId 366042940, started 5 Nov 23:29 IST, ran 774.8 s, exit code 0)

```
python experiments/quality_comparison.py --seeds 5 --device cuda
```

QUALITY RESULTS (real run, Tesla T4, FP16, 400 steps, kill at step 150,
2,000 eval examples, 5 seeds) — raw JSON:
`experiments/results/quality_comparison_20261105_181231.json`:

| seed | baseline accuracy | resumed accuracy | difference |
|-----:|------------------:|-----------------:|-----------:|
| 1 | 0.902 | 0.9055 | +0.0035 |
| 2 | 0.9015 | 0.903 | +0.0015 |
| 3 | 0.9035 | 0.904 | +0.0005 |
| 4 | 0.902 | 0.900 | -0.002 |
| 5 | 0.8995 | 0.9005 | +0.001 |

Mean baseline accuracy 0.9017, mean resumed accuracy 0.9026.
Mean difference +0.0009, 95% CI [-0.0016, +0.0034], worst seed -0.002
(seed 4). Quality Guard verdict PASS on all 5 seeds; canary bit-exact on
every seed.

Script's own claim line, copied exactly: "No degradation detected beyond 2 accuracy points at this sample size (mean +0.0009, 95% CI [-0.0016, +0.0034], 5 seeds, 2000 examples)."

Scope note from the script itself: "Both arms ran on one device. This compares resuming with a changed micro-batch, not two kinds of GPU."

**First attempt (5 Nov, unpatched pack): FAILED — and it found a real bug.**
Exact error: `KeyError: 'growth_factor'` from `GradScaler.load_state_dict`,
called by the resume path in `workers/runtime/gpuchain_runtime/run.py`. The
manifest stored only two of the scaler's five state values (`scale`,
`growth_tracker`), and `load_state_dict` requires all five. It only bites on
FP16 — BF16 (the 3060) and CPU never create a scaler — so the team's own runs
never hit it, and every FP16 resume from an FP16 checkpoint crashed.
**Fixed in this zip** (`workers/runtime/gpuchain_runtime/run.py`): the full
scaler state is saved (`scaler_to_manifest`), and restores go through
`scaler_from_manifest`, which fills values missing from old checkpoints with
the defaults `make_scaler` uses, so the leg-1 handover still resumes exactly.
Three regression tests (`ScalerStateRoundTrip` in
`workers/runtime/tests/test_runtime.py`) fail on the old code and pass on the
fix; runtime suite is now **50/50**. The run above was recommitted with the
patched pack.

## 4. What did not happen, and what failed

- **GPU inventory** from the four laptops: not collected yet (needs each
  laptop's `nvidia-smi` output; Vaibhav compiles the list).
- **Cross-GPU legs 2 and 3**: not run yet — leg 2 needs the 3060 (see above).
- **Demo job length and heat readings**: not done; they need the 3060.
- My earlier custom T4 middle-leg run (a CPU-made checkpoint resumed on a T4,
  canary difference 1.19e-07) and my custom honest-resume harness are in
  `extra_luna_work/` for the record. Piyush did not merge them — they overlap
  `infra/cross_gpu_notebook.ipynb` and `experiments/quality_comparison.py` —
  so they are **not** part of the submission evidence; the official runs in
  sections 2 and 3 replace them.
- A first attempt at the 5-seed run using my custom harness failed on Kaggle
  at seed 42 with the same exit-code-5 resume crash — the scaler bug in
  section 3 — and was abandoned in favour of the official script. The harness
  itself remains unmerged either way; it produced no results and is not
  evidence of anything.

## 5. Notebooks (Kaggle, account vaibhavparmar7002)

- Cross-GPU leg 1 (ran interactively, outputs in the notebook):
  https://www.kaggle.com/code/vaibhavparmar7002/notebook4ee5bf3997
- Quality comparison (committed run):
  https://www.kaggle.com/code/vaibhavparmar7002/notebook7904eda033
