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

The evaluation-set hashes and row counts match all five recipe test sets at
Git revision `458ed074eeb068bc30fef72912193842f7e776e6`. The product test set
has since been replaced by #73, so the old product scores do not measure the
current split. On Windows, checkout newline conversion can change
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

Scores describe these synthetic test sets and this particular untrained base-model
run. Neither model meets the recipe quality floor for ticket sorting, invoice
fields, product descriptions or FAQ. For review sentiment, only the 1.5B model
meets its floor (0.80). The ticket-sorter pass rates are 0.35 and 0.65, so
failure to meet the floor must not be described as a 0% per-example pass rate.
The original product-description split has high train/test similarity, so it
is a weak basis for judging a trained model's generalisation.
