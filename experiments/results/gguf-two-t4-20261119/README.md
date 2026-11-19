# Initial Q4/Q8 comparison, 19 November 2026

This is a first export comparison for
[issue #32](https://github.com/ekido-ai/ekido-internal/issues/32), using the
step-400 checkpoint from the two-T4 recovery run in
[PR #81](https://github.com/ekido-ai/ekido-core/pull/81). The checkpoint was
trained on 500 labelled ticket examples and evaluated on the same 100-row
synthetic ticket test set used here.

| Model | Accuracy | Difference from trainer | Within 0.05 tolerance |
| --- | ---: | ---: | --- |
| Original trainer | 0.82 | — | — |
| GGUF Q4_K_M | 0.71 | -0.11 | No |
| GGUF Q8_0 | 0.76 | -0.06 | No |

The 0.05 absolute accuracy tolerance was declared for this experiment; it is
not a published project policy. `summary.json` contains every prediction,
model SHA-256, test-set hash, tolerance and score. `run.txt` is the Kaggle
execution log. `run.py` is the exact executed private notebook script,
SHA-256 `63f2e419375f1bc0169c250f8c2cdbc5c1ba51cfee51e787c98b883ef26ca8f0`.
It embeds pinned worker and core source, consumes the step-400 checkpoint
from the earlier private run, merges it, converts with llama.cpp at
`f8caa5ea30b5775512906ae3b7ee53b21a7a6e1d`, and evaluates each GGUF with the
worker's llama-cli helper. All 200 pass/fail decisions and both score
differences were independently recomputed from the stored answers.

Neither quantized result meets the stated tolerance. This comparison changes
both representation and inference runtime, so it does not isolate quantization
as the cause of the score loss. The test set has been reused in earlier runs.
The first run stored the model hashes but did not retain the large GGUF files;
a follow-up is evaluating merged Hugging Face and F16 controls and retaining
the Q4/Q8 files. Do not treat this initial comparison as a successful export
quality gate.
