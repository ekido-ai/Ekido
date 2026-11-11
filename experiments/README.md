# Experiments

Raw results go in `experiments/results/` as JSON. **Every number we quote must trace back to a file here.**

## G1 feasibility spike

Build once, then run from the repo root in PowerShell:

```powershell
docker build -t gpuchain-runtime:spike -f infra/runtime.Dockerfile infra

docker volume create gpuchain_hf_cache

docker run --rm --gpus all `
  -v gpuchain_hf_cache:/hf_cache `
  -v "${PWD}\experiments:/work/experiments" `
  gpuchain-runtime:spike python experiments/spike_feasibility.py
```

It measures versions and native precision, speed and VRAM per micro-batch, whether a memory cap causes a real OOM, accuracy over a short job, checkpoint size, and evaluation time on GPU and CPU.

To run part of it, add for example `--only curve` or `--only sweep cap`. See `--help` for the other options.
