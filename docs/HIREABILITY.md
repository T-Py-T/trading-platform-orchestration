# Hireability and discoverability

Lean index for reviewers, recruiters, and search tools landing on this
repository. It does not change runtime behavior; remove or trim it without
affecting Compose, Kubernetes, or tests.

**Tip cite:** `71fb3a7` (current `main` tip prefix at authoring); Steward resolve
pending when the opening pull request for **Ship 262** merges. **tip≠READY** — no
release gate, score, certification, or live-trading authorization is implied.

## What / why / how

| Question | Short answer |
| --- | --- |
| **What** | Public orchestration contract: Docker Compose, Kubernetes bases/overlays, manifest tests, and operator docs for a componentized trading stack. |
| **Why** | Go API/TUI and C++ matching-engine implementations stay in private repos; this tree shows how they are wired, probed, and validated together. |
| **How** | Start with [README.md](../README.md) validation commands; render overlays with `DRY_RUN=true`; run `tests/test_gitroll_manifests.py` on pull requests. |

## Where to look

| If you want… | Start here |
| --- | --- |
| Architecture, ports, configuration | [README.md](../README.md) |
| Local workflow | [QUICKSTART.md](QUICKSTART.md) |
| Release process | [RELEASE.md](RELEASE.md) |
| Load-test procedure | [PERFORMANCE.md](PERFORMANCE.md) |
| Manifest regressions | [../tests/test_gitroll_manifests.py](../tests/test_gitroll_manifests.py) |
| Vulnerability reporting | [SECURITY.md](../SECURITY.md) |
| Terms of use | [LICENSE](../LICENSE) (MIT for this repository) |

Full-stack Compose builds additionally require sibling checkouts documented in
the README; manifest tests exercise the public configuration without claiming
production brokerage readiness.

## Suggested GitHub topics

For repository discoverability only (not quality endorsements):

`docker-compose` `kubernetes` `kustomize` `trading-platform` `grpc`
`postgresql` `devops` `manifest-testing` `health-checks` `orchestration`

## License pointer

Orchestration, tests, scripts, and documentation in this repository are under
[MIT](../LICENSE). Private Go and C++ component repositories are separate works
and are not covered by that license (see README License section).

## Reversibility

Delete this file and any README cross-links that point to it to revert the
discoverability lean without touching application images, manifests, or CI.
