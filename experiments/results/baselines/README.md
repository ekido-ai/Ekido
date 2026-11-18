# Supplied T4 baseline matrix, 17 November 2026

Vaibhav supplied the aggregate `source-t4-20261117.json` and the notebook
whose baseline cell produced `source-notebook-baseline-cell-28.txt`. The log
shows all ten jobs completing and their rounded pass rates and scores agree with
the aggregate. The original aggregate has SHA-256
`960c19facb958a0f95892e20bcf42917f096376c0a5a42711cd16459b0d2fd1d`.

The ten `recipe-model.json` files here are **derived from that aggregate**;
they are not the original per-job JSON files, which were not in the supplied
archive. The `run_at` value is the aggregate completion time, not a separate
start or finish time for each job. Predictions and individual per-example
scores are not present. These files cannot be used with the matrix runner's
`--resume` because the original run predates its code fingerprint fields.

The evaluation-set hashes and row counts match the merged Git versions of all
five recipe test sets. On Windows, checkout newline conversion can change
embedded newlines in invoice examples, so a hash from such a checkout can
differ; compare the Git version or a Linux checkout. Both model revisions in
the aggregate match the matrix runner's pinned revisions.

The submitted run used an earlier packaged runner and worker runtime. Its
packaged baseline.py, matrix runner, recipes.py and worker llm.py have SHA-256
respectively `50ec5978617cf94343029078046dd629e40e3952bc7cb37915f1792da6244dbd`,
`46726f6e59df05711e4af984d7504fd9989caa5e44b8e2b2823ce3372bb09137`,
`1c1a77ac39015a0e5f7700dd65a9cc3d890c82a3feebe22e566fc4650f607e80` and
`73b30a6f131e3f4d09d78cf81a65468c290044fb860c1a5c8f1f321eb2d479a3`.
The packaged generation implementation differs from the current worker runtime;
these records must not be presented as measurements of the updated code.

Scores describe this synthetic test set and this particular run. For example,
the 1.5B review-sentiment pass rate is 0.80: it meets the 0.80 floor but does
not exceed it. The product-description split has high train/test similarity,
so it is a weak basis for judging a trained model's generalisation.
