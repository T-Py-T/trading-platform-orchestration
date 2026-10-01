# Security policy

**Tip cite:** `bf79b4aa` (Ship 262 README hireability lean on `main`); Steward resolve
pending when the opening pull request for **Ship 266** merges. **tip≠READY** — no
release gate, score, certification, or live-trading authorization is implied.

Lean vulnerability reporting for this orchestration lab. Related docs:
[README.md](README.md), [`docs/HIREABILITY.md`](docs/HIREABILITY.md), [LICENSE](LICENSE).

## Scope

Supported version: current `main` only. This repository defines local Compose and
Kubernetes wiring for a componentized trading stack; it does not operate a hosted
brokerage or production trading service.

In scope: secrets in git, manifest/deploy misconfiguration in this tree, and
orchestration scripts under `scripts/`. Out of scope: defects in private Go/C++
component repos or third-party images—report those to their maintainers unless
the issue is how this repository references or configures them.

Runtime secrets and deployment credentials belong outside the repository. Never
commit secret values, decrypted configuration, private backups, or unredacted
load-test exports. `docker-compose.yml`, `k8s/`, and `scripts/` describe wiring;
they do not certify component implementations as secure. Manifest tests,
pre-commit checks, and dry-run deploy commands validate public configuration here
only—not a cluster, brokerage integration, or generated change.

## Report a vulnerability

Do not open a public issue for an unpatched vulnerability.

Email the repository owner at [tnt850910@aol.com](mailto:tnt850910@aol.com). When
the repository Security tab offers it, you may also use GitHub's private
vulnerability reporting.

Include the affected commit, the vulnerable path, the impact, and the smallest
reproduction that does not expose sensitive data. You can expect an
acknowledgment within seven days. A fix schedule depends on severity and the
affected component.

## Keep reports and evidence safe

- Do not send or commit brokerage credentials, API keys, database passwords,
  TLS private keys, Kubernetes secrets, or personal data.
- Do not attach unredacted Compose or overlay files that embed live credentials,
  production connection strings, or customer order data.
- Use synthetic credentials, local fixtures, and dry-run deployment commands
  when reproducing orchestration defects.
- Treat captured third-party output under its original license and terms.

## Reversibility

Delete or trim this file and any README or hireability cross-links that point to
it to revert the discoverability lean without touching images, manifests, or CI.
