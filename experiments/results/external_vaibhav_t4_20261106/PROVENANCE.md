# Vaibhav T4 evidence received 6 November 2026

Selected files copied without executing code from `asli_web3_complete.zip`, SHA-256 `eccbbf6e52e58c2e9de15e0bac14ceb36eed814b55b47829c649f863180b5481`. Original paths were under `asli web3/GPUChain_all_work_2026-11-05/07_updated_evidence/`.

Both checkpoint tensor file sizes and SHA-256 hashes were checked against `handover_t4/manifest.json`. This confirms integrity relative to that manifest; it does not independently establish GPU origin, execution, model correctness or quality. The supplied metadata records a Tesla T4 FP16 start leg from step 0 to 150. No RTX 3060 resume or round trip was supplied. Model revision `main` and the all-zero dataset fingerprint are not reproducible pins; preserve the original files without rewriting their metadata.

The repository CPU loader subsequently accepted the checkpoint: 28 trainable tensors and 84 optimizer tensors passed file/hash, dtype, finite-value and optimizer-structure checks; the spec hash matched, and the legacy scaler state loaded into a CPU GradScaler after conversion. The expected parameter shapes in this check were read from the checkpoint itself, so this does not independently verify compatibility with the model or demonstrate GPU execution.

The supplied `quality_comparison_20261105_181231.json` records five same-T4 trials, 2,000 evaluation examples and a mean resumed-minus-baseline accuracy difference of +0.0009 with reported 95% interval [-0.0015595, +0.0033595]. The sender's audit says this comparison resumed a saved intermediate checkpoint and did not inject an actual process kill. This is neither an independently verified execution nor cross-GPU evidence.
