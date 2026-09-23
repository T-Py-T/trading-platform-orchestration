# Security policy

## Supported code

The current `main` branch is the only supported version. This repository is a
local orchestration lab for composing and deploying the trading platform stack;
it does not operate a hosted brokerage or production trading service.

## Report a vulnerability

Do not open a public issue for an unpatched vulnerability.

Email the repository owner at [tnt850910@aol.com](mailto:tnt850910@aol.com). When
the repository Security tab offers it, you may also use GitHub's private
vulnerability reporting.

Include the affected commit, the vulnerable path, the impact, and the smallest
reproduction that does not expose sensitive data. You can expect an
acknowledgment within seven days. A fix schedule depends on the severity and
the affected component.

## Keep reports and evidence safe

- Do not send or commit brokerage credentials, API keys, database passwords,
  TLS private keys, Kubernetes secrets, or personal data.
- Do not attach unredacted Compose or overlay files that embed live credentials,
  production connection strings, or customer order data.
- Use synthetic credentials, local fixtures, and dry-run deployment commands
  when reproducing orchestration defects.
- Treat captured third-party output under its original license and terms.

## Repository boundary

Runtime secrets and deployment credentials belong outside the repository. Never
commit a secret value, decrypted configuration, private backup, or unredacted
load-test export.

`docker-compose.yml`, `k8s/`, and the helper scripts in `scripts/` define how
components are wired on your machine or cluster. They do not certify the Go
API/TUI, C++ matching engine, PostgreSQL, or any third-party image as secure.

Manifest tests, pre-commit checks, and dry-run deploy commands validate the
public configuration in this repository. Local checks do not certify a cluster,
brokerage integration, or generated change as secure.
