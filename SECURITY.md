# Security policy

Ekido is a prototype on the Base Sepolia **test network**. The contracts are **not audited**. Never send real funds to any address in this repository, and never use a wallet that holds real money with it.

## Reporting a vulnerability

Please report security problems privately, not in a public issue:

1. Open the repository's **Security** tab and choose **Report a vulnerability**.
2. Say what you found, how to reproduce it, and what an attacker could gain.

We'll acknowledge the report and agree a time to fix it before anything is published. Please test only against your own wallets and jobs, and don't degrade the public test network for other people.

## In scope

- `contracts/`: the escrow and registry contracts (payout rules, signature checks, refunds, disputes).
- `apps/coordinator/`: the coordinator API, including rate limits, join rules and settlement.
- `workers/`: the provider agent, training runtime and verifier, including checkpoint loading.
- `apps/web-combined/`: the web app, including wallet sign-in and the in-browser verification of payouts.

## Known limitations (not vulnerabilities)

- Verifiers and the dispute arbiter are run by the team, so two colluding verifiers could approve bad work.
- A provider can read training data in GPU memory; only public data should be used.
- Provider telemetry is self-reported and never decides payment.

The design behind these choices is in [`docs/security-and-privacy.md`](docs/security-and-privacy.md).
