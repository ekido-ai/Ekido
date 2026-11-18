# Supplied T4 runtime evidence

These files preserve results supplied in `ekido-delivery-light.zip` for the
ticket-sorter experiments. They are reports from the supplied Kaggle runs, not
independent reruns. `c6-c10-summary.json`, `c10-export.json`,
`c6-training-a2.json`, `c14-summary.json`, `c14-distill-a2.json`, and
`c14-student-dataset.jsonl` correspond respectively to `SUMMARY8.json`,
`C10.json`, `train_a2_evidence.json`, `SUMMARY4.json`,
`distill_a2_evidence.json`, and `student_dataset.jsonl`. The llama-cli log was
renamed to `.txt` for inclusion. The original bytes are preserved.

## C6: training

The supplied summary reports 0.81 accuracy on 100 test examples for both step
160 and step 220 of attempt a2, against a floor of 0.80. It selects step 160.
The same test set was used to compare checkpoints, so this score is not an
independent post-selection holdout. The supplied a2 evidence reports the final
step 220 evaluation; the step 160 result comes from the summary.

The supplied C6 checkpoint archive contains step 160. Its manifest names base
revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` and dataset SHA-256
`2a3e623bdcf690f3301894c3b1b75e0e72bb8e63a99245e91760f4765083debc`.
Its trainable and optimizer files matched the manifest SHA-256 values
`6fb2c98344aee6764e75b58b8a20b25ebe498a9482c12211c5d13c2470690012`
and `43ed44494826db6b7932486a4f7a7bf2adc22f89791f88c1e7ee0584325bb57f`.
The archive is not included in this repository.

## C10: export

The supplied log reports a successful local llama-cli invocation of the Q8
export and the answer `order`. The export files themselves were not present in
the light delivery; the log and reported file sizes do not establish staging CPU
deployment or independently verify the exported artifacts.

## C14: distillation

The supplied a2 run reports 0.53 accuracy against a 0.80 floor and a 0.65 base
score. The summary also reports 0.55 for a1, although it labels a2 the best
attempt; the reported scores do not support that label. The included dataset
hash is `887863ad8d66638af5aadec17517fc8319c085d9ded8bfb4d64d00e0496e35ab`.
The supplied C14 step-320 archive names the same dataset hash and base revision
as above. Its trainable and optimizer files matched their manifest hashes
`9338f1f09d863970c12224627bb5eb634604c69165f12983473f8ab8661273ee`
and `2940c38ebaee74ba77609f244c8e4ec80847b32ba364428a126009b59c3b735c`.
The archive is not included in this repository. Further training and evaluation
are required before claiming the quality floor has been met.
