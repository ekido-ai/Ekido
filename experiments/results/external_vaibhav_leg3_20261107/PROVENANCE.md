# Cross-GPU leg 3, from Vaibhav (7 Nov 2026)

Copied, without running any code, from `C:\Users\Mahak\Downloads\attachments (1).zip`, the Gmail wrapper. The inner `GPUChain_leg3_outputs_2026-11-07.zip` has SHA-256 `c5210339529d2f7f94b7731639f9108ae1027e9657dc563ccfa422535de81d0c`, which matches what Vaibhav quoted. All six files listed in `SHA256SUMS.json` matched.

**Round trip:**

| Leg | GPU | Steps | Precision and batching | Accuracy |
|---|---|---|---|---|
| 1 | Tesla T4, Kaggle | 0 to 150 | FP16, 16 x 2 | 0.896 |
| 2 | RTX 3060 Laptop, this laptop | 150 to 200 | BF16, 8 x 4 | 0.906 |
| 3 | Tesla T4, Kaggle | 200 to 250 | FP16, 16 x 2 | 0.905 |

Accuracy is on 2,000 examples. Leg 3's saved canary, 0.06621839851, equals the canary in our leg 2 step-200 manifest. That links leg 3 to the checkpoint the 3060 produced.

**Limits:** one run and one seed. Not a process kill. It doesn't show equivalence with an uninterrupted run. Legs 1 and 3 are separate Kaggle sessions, with no proof they used the same physical card. The intermediate manifests at steps 175 and 225 weren't kept, so the hash chain between legs can't be walked end to end. The original T4 handover uses model revision `main` and an all-zero dataset fingerprint.
