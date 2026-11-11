# Changelog

All notable changes to this project are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-11-11

The first public release: the hackathon build, continued as a personal project.

### Added

- **Recovery across GPUs:** failure detection (process exit and heartbeats), fencing tokens, checkpoint re-testing, the elastic compiler with a real memory probe, restore with a canary-loss check, and automatic resume.
- **Quality Guard:** a paired bootstrap test against the last accepted checkpoint, fixed by hash before training, with a 2-of-3 verifier quorum and rollback.
- **Settlement on Base Sepolia:** `GPUChainEscrow` and `ProviderRegistry`, EIP-712 verdicts, a dispute window with a bond, a permissionless timeout refund, pull payments, and an 8% protocol fee on accepted work only.
- **Transparency:** the browser rebuilds a double-entry journal from chain events, checks proof of reserves and runs a 5-way reconciliation; a chain indexer speeds this up without being trusted.
- **Web app:** landing page with a live "pull the plug" demo, mission control, recovery, quality and settlement views, on-chain books, accounts, an owner console, provider onboarding, help, status, privacy, terms and security pages, and a few easter eggs.
- **Wallet sign-in (EIP-4361)** and read-only demo accounts for a client, a provider and the owner.
- **Provider kit** for Windows, macOS and Linux, with on-chain listing from the provider's own wallet.
- **Operations:** `/readyz` deep health checks, per-client rate limits, hardened provider joins, security headers, a 5-minute health monitor, daily integrity-checked backups copied to a private Cloud Storage bucket, and email alerts from uptime checks.
- **Evidence:** recorded GPU runs (4 and 9 Nov), a cross-GPU run (T4 → RTX 3060 → T4), quality and false-rejection measurements, and a real testnet settlement, all under `experiments/results/`.
- **Continuous integration:** Python suites, the web app's typecheck, unit tests and production build, and the Foundry tests on every pull request; CodeQL for Python, TypeScript and workflows; dependency review; Conventional Commit PR titles.
- **Continuous deployment:** the server deploys `main` itself once CI is green, without any credential in GitHub. It compares the new code with what's running, waits for unfinished jobs, installs web dependency updates with `npm ci`, and puts the previous version back if anything fails. A Deploy workflow confirms the live site runs the merged commit.
- **Repository protection:** pull requests and green checks required on `main`, no force pushes, secret scanning with push protection, Dependabot alerts and security updates, private vulnerability reporting.

### Security

- The artifact store accepted a digest with a trailing newline (`re.match` with `$`); it now uses `fullmatch` and keeps every path inside the store.
- Event reducers refuse `__proto__`, `constructor` and `prototype` as provider ids.
- `minimatch` moved from 10 to 11 to fix a denial-of-service advisory in the lint toolchain.
- Third-party GitHub Actions are pinned to commit SHAs.

### Fixed

- The Windows provider setup stopped immediately on any PC without Python 3.12 installed through the `py` launcher.
- The network's own CPU provider did not come back after a server restart.
- The header "Sign in" button showed an error without a browser wallet instead of offering the demo accounts.
