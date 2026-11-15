# Contributing to Ekido

Thanks for your interest. Ekido is a small project, so a clear issue or a focused pull request helps most.

## Before you start

- For anything bigger than a small fix, open an issue first so we can agree on the approach.
- Read [`docs/system-design.md`](docs/system-design.md) for how the pieces fit, and the README of the package you're changing.

## Ground rules

- **Test networks only.** Never commit `.env` files, private keys or real wallet addresses that hold funds. Use testnet-only wallets.
- **Evidence over claims.** Any number in docs or the UI must trace to a raw file in `experiments/results/`. Label simulated, synthetic or CPU-only results as such, and never present them as GPU results.
- **No pickle in checkpoints.** Checkpoints are safetensors and JSON only; `torch.load` stays out of load paths.
- **Keep the logical step invariant.** The runtime may change micro-batch, accumulation and precision between GPUs, never the maths of a logical training step.

## Making a change

1. Fork the repository and create a branch.
2. Make the change with tests next to it.
3. Run the tests for what you touched:
   - Contracts: `forge test` in `contracts/`
   - Python packages: `pytest` in `packages/ekido_core`, `apps/coordinator`, `workers/agent`, `workers/runtime` or `workers/verifier`
   - Web app: `npx vitest run` and `npx tsc --noEmit` in `apps/web-combined/`
4. Open a pull request that says what changed, why, and how you tested it. Say plainly what you didn't run.

## Style

- Python 3.12, type hints, small functions, clear names.
- TypeScript strict mode; React components in `apps/web-combined/src/components`.
- Solidity: checks-effects-interactions, custom errors, and a test for every revert path.
- User-facing text: plain words, sentence case, active voice.

This project is not open source: all rights are reserved (see [`LICENSE`](LICENSE)). Contributions are by invitation, and by contributing you agree that your contribution becomes part of the project under that license.
