# Real AG News identity check — 7 November 2026

The official `experiments/prepare_identity.py` was run against Hugging Face with Python 3.12.14, datasets 5.1.0 and huggingface_hub 2.4.0. It wrote `identity_agnews_20261107.json` alongside this file.

Command (from this patch root, after installing the dependencies):

```text
python experiments/prepare_identity.py --out experiments/results/identity_agnews_20261107.json
```

The identity records DistilBERT model revision `12040accade4e8a0f71eabdb258fecc2e7e948be` and AG News dataset revision `eb185aade064a813bc0b7f42de02595523103ca4`.

The complete ordered splits were loaded again in offline mode from the local cache and checked by the current patch's `check_split`:

```text
train PASS 120000 65011f777297ca64a4aa14715f9ec33ecdd63fad0afcc070141349fe0584a0e5
test PASS 7600 510142e216f159859263fd45690bf1b24e460dc3bd5ac6e36df124f7fd7de092
```

This verifies the generated identity against a second read of the same downloaded cache. It is not an independent download, proof of model weights, a training/evaluation run, GPU evidence, or a cross-GPU result. The earlier T4 handover remains unchanged.

`hf_revision_metadata_20261107.json` records a separate Hugging Face metadata lookup confirming the model and dataset commit IDs and the published weight-file SHA-256. The full 267,954,768-byte model weight file was subsequently downloaded in four byte ranges, and its combined SHA-256 matched the published hash. The result is in `model_file_integrity_20261107.json`. This is a file-integrity check, not an executed-model result.

Local GPU inventory check (`Get-CimInstance Win32_VideoController`): Intel(R) HD Graphics, driver 20.19.15.4835, AdapterRAM 1073741824 bytes as reported by Windows. No NVIDIA driver utility was found. Compute capability and NVIDIA CUDA support: not applicable/not detected. This is not an inventory of teammates' machines and Windows AdapterRAM may not reflect the device's usable shared memory.

Still pending: actual model runtime/evaluation with pinned inputs, real GPU probation measurement, second-GPU handover and return, teammates' inventories, and demo heat/timing.
