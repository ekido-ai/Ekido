# G1 Feasibility Results

**Source:** `results/spike_20261104_163137.json`. One run, one seed (1337), on 4 Nov 2026. Treat these as starting values, not benchmarks.

**Setup:** RTX 3060 Laptop (6 GB, compute capability 8.6), Docker Desktop, torch 2.15.0+cu132, transformers 5.22.1, peft 0.21.2, DistilBERT with LoRA (r=8), AG News, max length 128.

## Gate result

| Question | Result | Pass? |
|---|---|---|
| Does GPU training work in Docker? | Yes. Wheel built for CUDA 13.2 works on a driver reporting 13.0 | Yes |
| Is BF16 native here? | Yes | Yes |
| Is training fast enough? | 13.7 logical steps/s over the 300-step job | Yes |
| Is accuracy usable? | 90.33% on all 7,600 test examples after 300 steps | Yes |
| Does a memory cap cause a real OOM? | Yes, a genuine `torch.OutOfMemoryError` | Yes |
| Same checkpoint on a T4 | **Not run yet** | Open |

## Measurements

**Accuracy on the full test set (BF16, micro-batch 32):**

| Step | 0 | 50 | 100 | 150 | 200 | 250 | 300 |
|---|---|---|---|---|---|---|---|
| Accuracy | 24.95% | 88.00% | 88.51% | 89.68% | 89.86% | 90.16% | 90.33% |

Accuracy never dropped between these evaluations. Bigger dips may still occur at other seeds or finer intervals.

**Speed and memory (logical batch 32, 10 steps each, so speed is rough):**

| Micro-batch x accumulation | BF16 steps/s | BF16 peak reserved | FP16 steps/s | FP32 steps/s | FP32 peak reserved |
|---|---|---|---|---|---|
| 32 x 1 | 16.2 | 996 MiB | 14.5 | 6.8 | 1382 MiB |
| 16 x 2 | 15.5 | 704 MiB | 14.4 | 6.6 | 836 MiB |
| 8 x 4 | 11.6 | 544 MiB | 11.3 | 6.1 | 586 MiB |
| 4 x 8 | 5.8 | 454 MiB | 4.8 | 5.6 | 420 MiB |
| 2 x 16 | 2.8 | 424 MiB | 2.6 | 3.4 | 386 MiB |
| 1 x 32 | 1.4 | 394 MiB | 1.4 | 1.7 | 336 MiB |

**Memory cap (BF16):**

| Cap | First micro-batch that fit |
|---|---|
| 1024 MiB and above | 32 |
| 768 MiB | 16 |
| 512 MiB | 4 |

**Checkpoint:** 2.97 MB trainable + 5.94 MB optimizer = 8.9 MB. Saved in 12 ms to the container's temp disk. Upload time isn't included.

**Evaluation of all 7,600 examples:** 28 s on GPU at FP32. CPU took 25 s for only 500 examples. Across those 500, CPU and GPU made 0 different correct/incorrect calls.

**Heat:** the GPU reached 86°C during training on this run.

**Token length:** p50 51, p99 126, with 0.88% of training examples truncated at 128.

## What this changes in the plan

1. **Memory caps must be far lower than planned.** This job needs under 1 GB, so a 3 GB cap wouldn't force any adaptation. Starting values, applying the compiler's 85% margin:
   - Provider A: full 6 GB, keeps micro-batch 32.
   - Provider B: 768 MiB. The 653 MiB limit rules out micro-batch 16 at 704 MiB, so it should adapt to 8 x 4 at about 11.6 steps/s.
   - Provider C: 300 MiB. Below the smallest measured need (336 MiB), so it should be refused.
2. **300 steps is too short for a live demo.** It takes about 22 s, and a 4-minute story needs a longer job. Estimated at 1,200 steps (about 90 s on Provider A), but this needs a rehearsal. Longer jobs should also finish above 90%, though that hasn't been measured.
3. **Full evaluation is too slow to run often.** At 28 s per checkpoint on GPU, the demo should evaluate at handover and at the end only, or use a smaller stratified set. A CPU verifier can't do the full set in demo time (estimated at over 6 minutes).
4. **A shared GPU limits verifier speed.** Evaluation and training compete on the one GPU, so one more reason to evaluate only at handover and the end.
5. **Quality margin:** the 2-point margin looks workable, since the 95% half-width on the full set is about 0.67 points unpaired. It still needs testing against honest resumed runs on the real workload.
6. **Heat is a real demo risk (R5).** Rehearse on AC power with cooling, and watch the temperature.

## Still unmeasured

- Honest resume on the real workload after changing micro-batch, and its quality difference
- Whether poison and LR tampering get rejected on the real workload
- Multiple seeds
- Real recovery time on the GPU, including probes
- Any second physical GPU
