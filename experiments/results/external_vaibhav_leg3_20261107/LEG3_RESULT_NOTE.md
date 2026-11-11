# Cross-GPU round trip: T4 -> RTX 3060 -> T4 (7 Nov 2026)

All numbers are read from the evidence files. Leg 3 outputs match their `SHA256SUMS.json`. Leg-3 zip SHA-256: `c5210339529d2f7f94b7731639f9108ae1027e9657dc563ccfa422535de81d0c`.

| Leg | Machine | Steps | Precision | Micro-batch x accumulation | Accuracy (2,000 ex.) | Canary saved / measured |
|---|---|---|---|---|---|---|
| 1 | Kaggle Tesla T4 (CC 7.5), 5 Nov | 0 to 150 | fp16 | 16 x 2 | 0.896 | none (first leg) |
| 2 | RTX 3060 Laptop (CC 8.6, 6143 MiB), run by Piyush | 150 to 200 | bf16 | 8 x 4 | 0.906 | 0.043106809 / 0.043106779 |
| 3 | Kaggle Tesla T4 (CC 7.5, 14911 MiB), this notebook | 200 to 250 | fp16 | 16 x 2 | 0.905 | 0.066218399 / 0.066218361 |

Leg 3 details: 55.3 s, peak GPU memory 687.8 MiB, exit code 0. Software: torch 2.11.0+cu130, Python 3.13.16, CUDA 13.0, Linux. Command: `cross_gpu_resume.py resume --checkpoint <leg-2 folder> --out /kaggle/working/back_home --steps 50 --micro-batch 16 --device cuda`.

## What was checked

- The leg-2 files the notebook read match Piyush's `SHA256SUMS.json` (all 5 files).
- The "saved" canary leg 3 compared against (0.06621839851140976) is exactly the canary in leg 2's step-200 manifest.
- Canary difference on leg 3: 3.7e-08 absolute, 5.6e-07 relative.
- Spec and `immutable_hash` are identical across legs.
- The leg-3 manifest records the 3060 as the previous leg (bf16, 8 x 4). The leg-2 manifest records the T4 (fp16, 16 x 2).
- The FP16 GradScaler started fresh on leg 3 (leg 2 was bf16, which has none); its state at step 250 is scale 65536, growth_tracker 50.

## What this does and does not show

- It shows: a checkpoint trained on a T4 resumed on an RTX 3060 with different precision and micro-batch, then resumed again on a T4, restored correctly each time (canary matches) and kept training.
- It does not show: that the result equals an uninterrupted run, or that quality is preserved. Accuracy went 0.896, 0.906, 0.905, but one-point differences on 2,000 examples are within the sampling noise the plan itself describes (about 1.3 points half-width), so no trend should be read into them.
- One run, one seed.
- Not a process kill. Each leg was a planned resume from a saved checkpoint.
- Leg 1 and leg 3 are both T4 sessions on Kaggle. The notebook does not prove they were the same physical card.
- The direct hash link from step 250 back to leg 2's step-200 manifest cannot be checked from these files: leg 3 saved checkpoints at step 225 and 250 and the script keeps only the newest, so the step-225 manifest (the parent of step 250) is not retained. The same applies between legs 1 and 2.
- The whole chain inherits the historical T4 handover limitation: model revision `main` and an all-zero dataset fingerprint in the spec. It was not repinned.

## Files

`leg3_evidence.json`, `leg3_manifest.json`, `leg3_spec.json`, `leg3_checkpoint_file_sha256.json` (hashes of the leg-3 tensors; the tensors themselves stayed on Kaggle and are not sent), `leg3_run.log`, `environment.json`, `SHA256SUMS.json`.
