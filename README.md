# Trading Platform Orchestration

![Test Suite](https://github.com/T-Py-T/trading-platform-orchestration/actions/workflows/test.yml/badge.svg?branch=main)

**The public contract for how a split trading stack is wired: ports, probes, secrets, and the tests that keep Compose and Kubernetes from drifting apart.**

The Go API, the C++ matching engine, and their Dockerfiles are not in this repository. You cannot clone a running exchange from here. What you can clone is the agreement those processes would have to share, and you can fail a pull request when that agreement breaks.

```text
this repository
  docker-compose.yml
  k8s bases and dev/production overlays
  deploy.sh (render first, apply only if you insist)
  tests that read the YAML
        | configures                         | configures
        v                                    v
  HTTP and WebSocket API              gRPC matching engine
  not published here                  not published here
        |
        v
  PostgreSQL (official image, pin is in the Compose file)
```

No UI mock, no screenshot, and no performance figure belongs on this page. None are in the tree.

## Why try it

When each runtime lives in its own repository, the integration surface hides in a wiki and three Compose files. A port change looks local until a probe or an ingress still points at the old one.

This repo makes that surface a diff. A manifest test fails if a service-account token is mounted, an image tag is floating, a credential value is committed, the ingress port disagrees with the nginx listener, or the API liveness probe is pointed at an endpoint that is supposed to degrade. `docs/gitroll-triage.md` is the ledger of findings that produced several of those rules.

## Worked example

The interesting rule is a probe split, and you can watch the test defend it without a cluster.

The API's `/healthz` is allowed to return `503` when the write-behind outbox is too full or too stale. That is a readiness signal. It is a bad liveness signal: a busy replica would be restarted while it still holds unflushed writes. The backend manifest therefore uses a TCP liveness probe on port `8000` and keeps HTTP `/healthz` for readiness.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest \
  tests/test_gitroll_manifests.py::test_backend_liveness_does_not_use_degrading_health_endpoint \
  -v
```

That test passed. It compares the whole probe, so a "harmless" edit to the path, delay, or failure threshold fails the same way a type change does.

The production overlay renders two `tcpSocket` probes (backend and engine):

```sh
cd k8s
kubectl kustomize overlays/production | grep -c 'tcpSocket'
```

That count was `2`.

## Honest demo

Everything below was run from this public tree. Nothing below starts a stack.

| Command | Result here |
| --- | --- |
| `python -m pytest tests/test_gitroll_manifests.py -v` | 6 passed |
| `pre-commit run --config .pre-commit/.pre-commit-config.yaml --all-files` | passed (whitespace, YAML, yamllint, black, ruff, detect-secrets, shellcheck, markdownlint) |
| `DRY_RUN=true ./deploy.sh dev` and `production`, from `k8s/` | rendered manifests, did not contact a cluster for apply |
| `kubectl kustomize overlays/production` | rendered; `tcpSocket` count 2 |
| `docker compose config` | **not run successfully.** Docker Engine 29.8.2 on this machine has no Compose plugin (`docker: unknown command: docker compose`). The plugin was not installed for this page. |
| `podman-compose config`, with placeholder secrets | rendered the graph and stopped. It did not build or start containers. |

`podman-compose config` is not a second supported entrypoint. It was a read-only check after the documented Docker Compose v2 command could not start. The rendered build contexts are sibling directories named in `docker-compose.yml`. Those directories are not part of this repository. This page does not link them and does not describe their internals.

Not run, on purpose: `docker compose up`, `make up`, `make test`, `scripts/build-docker-images.sh`, and `./deploy.sh` without `DRY_RUN=true`. Those need the unpublished components or a cluster.

**No throughput, latency, fill, or profit-and-loss number is published here.** Replica counts and memory limits in the overlays are configuration, not measurements. [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md) describes how a load run would have to be recorded. It does not contain a result.

## Getting started

Python 3.11 or newer. `kubectl` for `kustomize` and `deploy.sh`. Docker Compose v2 only if `docker compose version` already works. No cluster credentials.

```sh
git clone https://github.com/T-Py-T/trading-platform-orchestration.git
cd trading-platform-orchestration
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest tests/test_gitroll_manifests.py -v
python -m pip install pre-commit
pre-commit run --config .pre-commit/.pre-commit-config.yaml --all-files
```

Those six tests are the `Python Tests` job. They stay offline. `tests/integration_test.py` targets a historical Python API that is not in this platform. `pytest.ini` collects `test_*.py` only, so that file is not part of the run.

Compose, when the plugin exists, interpolates secrets and validates the graph. It does not build:

```sh
export POSTGRES_PASSWORD=placeholder
export JWT_SECRET=placeholder
export DATABASE_URL="postgres://trading_user:${POSTGRES_PASSWORD}@postgres:5432/trading_db?sslmode=disable"
docker compose config
```

Any placeholder satisfies interpolation. If the command is `unknown command: docker compose`, stop. Do not switch to `compose up`.

Preview both overlays from `k8s/`. Dry-run renders with `kubectl kustomize` and returns before any apply:

```sh
cd k8s
DRY_RUN=true ./deploy.sh dev
DRY_RUN=true ./deploy.sh production
```

[`docs/QUICKSTART.md`](docs/QUICKSTART.md) repeats these public steps. Later sections of that guide assume unpublished sibling checkouts. They will not work from this tree alone. Stop at the dry run.

## Configuration reference

Secrets are required in Compose and in Kubernetes. Compose fails when they are unset. `deploy.sh` refuses a non-preview deploy until they are present, and it creates Secret objects from the environment at apply time. No Secret manifest is committed. A test enforces that.

| Variable | Default | Purpose |
| --- | --- | --- |
| `POSTGRES_PASSWORD` | required | PostgreSQL password |
| `DATABASE_URL` | required | API database URL |
| `JWT_SECRET` | required | Signing secret |
| `ENGINE_ADDR` | `hft-engine:50051` | Matching-engine gRPC address |
| `ENGINE_ENABLED` | `true` | Engine client toggle |
| `WRITE_BEHIND` | `true` | Buffered database writes |
| `OUTBOX_BUFFER` | `10000` | Outbox capacity |
| `OUTBOX_BATCH` | `50` | Max write batch |
| `OUTBOX_FLUSH` | `50ms` | Partial-batch flush |
| `OUTBOX_LAG_THRESHOLD` | `5s` | Outbox lag health threshold |
| `LOG_LEVEL` | `info` | Log level |
| `LOG_FORMAT` | `json` | Log format |
| `APP_ENV` | `production` | Environment selector |

| Service | Port | Protocol | Where |
| --- | --- | --- | --- |
| Backend API | `8000` | HTTP and WebSocket | Compose and Kubernetes |
| Matching engine | `50051` | gRPC | Compose and Kubernetes |
| Matching engine | `9001` | UDP | Kubernetes only |
| PostgreSQL | `5432` | TCP | Compose and Kubernetes |
| Nginx ingress | `80` and `8080` | TCP, listener `8080` | Kubernetes only |

| Setting | `dev` | `production` |
| --- | --- | --- |
| Backend replicas | 1 | 4 |
| Backend memory | 128Mi | 512Mi |
| Backend CPU | 250m | 1000m |
| Engine memory | 512Mi | 1Gi |
| Engine image tag | `dev` | `2a722ff` |
| Image pull | `Never` | `IfNotPresent` |
| Prometheus annotations | no | yes |

Both overlays also generate an `hft-config` ConfigMap. No workload references it yet. The API reads `backend-config`. Render an overlay to see which ConfigMap a container actually mounts.

```text
docker-compose.yml
k8s/base/                  namespace, postgres, engine, backend, nginx
k8s/overlays/dev/          one backend replica, local tags
k8s/overlays/production/   four backend replicas, pinned tags
k8s/deploy.sh              render, then optionally apply
tests/test_gitroll_manifests.py
scripts/                   database bootstrap, image build, load generators
docs/QUICKSTART.md
docs/RELEASE.md
docs/PERFORMANCE.md
docs/gitroll-triage.md
```

## Contributing

Changes to the Compose file, manifests, overlays, tests, scripts, and docs are in scope. Behavior that lives only in the unpublished Go or C++ trees cannot be fixed from here. What can be fixed here is how this repo points at them.

1. Branch from `main`.
2. If the change is a rule that must not regress, extend `tests/test_gitroll_manifests.py`.
3. Run `python -m pytest tests/test_gitroll_manifests.py -v` and `pre-commit run --config .pre-commit/.pre-commit-config.yaml --all-files`.
4. Open a pull request against `main`.

Vulnerability reports do not belong in a public issue. [SECURITY.md](SECURITY.md) is the private path and the scope boundary. [`docs/RELEASE.md`](docs/RELEASE.md) is the checklist for an orchestration revision. This repository does not publish a release or deploy an environment by itself.

## License

Orchestration files, tests, scripts, and documentation in this repository are [MIT](LICENSE). Other component repositories are separate works and are not covered by this license.
