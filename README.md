# Trading Platform Orchestration

![Test Suite](https://github.com/T-Py-T/trading-platform-orchestration/actions/workflows/test.yml/badge.svg?branch=main)

**The deployment contract for a componentized trading platform: Compose wiring,
Kubernetes manifests, a dry-run deploy script, and tests that keep the two in
agreement.**

A trading platform split across several language runtimes has to agree on the
boring things — which port the API listens on, which address the matching engine
answers on, which probe decides a replica is dead, how much memory each
container may take, and where the credentials come from. This repository is
where that agreement is written down, versioned, and tested.

## What is in this repository

- `docker-compose.yml` — the local multi-service composition: service graph,
  startup ordering, health checks, published ports, and named volumes.
- `k8s/` — Kubernetes bases plus `dev` and `production` Kustomize overlays, and
  `deploy.sh`, which renders an overlay locally before it touches a cluster.
- `tests/test_gitroll_manifests.py` — six regression checks over the manifests:
  service-account tokens stay off and ephemeral storage is bounded, images are
  pinned to auditable tags, no credential value is committed, the ingress port
  matches the listener in `nginx.conf`, the API liveness probe is not the
  degrading health endpoint, and `DRY_RUN=true` never contacts a cluster.
- `scripts/` — database bootstrap, image build, and load-generation helpers.
- `docs/` — operator guides for local integration, releases, and load testing.
- `.pre-commit/` and `.github/workflows/test.yml` — the lint and test gate that
  runs on every pull request.

## What is not in this repository

- The Go API and TUI source.
- The C++ matching engine source.
- The Dockerfiles those components build from, and the engine container image.

Those components live in separate repositories that are **not public**. You
cannot clone a runnable trading stack from here, and nothing below will ask you
to try. What you can do is read, validate, and change the contract that would
wire such a stack together.

```text
┌──────────────────────────────────────────────────────────────┐
│ THIS REPOSITORY                                              │
│ Compose file · Kubernetes bases and overlays · deploy script │
│ ports · env vars · probes · resource limits · manifest tests │
└───────────────┬──────────────────────────┬───────────────────┘
                │ configures               │ configures
        HTTP / WebSocket                 gRPC
                │                          │
      ┌─────────▼──────────┐    ┌──────────▼──────────┐
      │ Go API and TUI     │    │ C++ matching engine │
      │ not in this repo   │    │ not in this repo    │
      └─────────┬──────────┘    └─────────────────────┘
                │ configures
      ┌─────────▼──────────┐
      │ PostgreSQL         │
      │ official image     │
      └────────────────────┘
```

## Why it exists

When each component owns its own repository, the integration surface has no
natural home. It ends up duplicated in a wiki, in someone's shell history, and
in three slightly different Compose files. Drift is invisible until a deploy
fails.

Keeping the contract in one repository makes it reviewable. A change to a port,
a probe, a resource limit, or a credential path arrives as a pull request with
a diff, and the manifest tests fail if it breaks a rule the platform depends on.
Several of those rules exist because a static analysis pass found the opposite
committed here first; `docs/gitroll-triage.md` is the ledger of what was found
and what was changed.

## Getting started

Everything in this section runs against a fresh clone of this repository alone.
No cluster, no credentials, no sibling checkouts.

### Requirements

- Python 3.11 or newer
- The Docker CLI with Compose v2, for the configuration check only
- `kubectl`, for rendering the overlays with its built-in Kustomize

### 1. Run the manifest tests

```bash
git clone https://github.com/T-Py-T/trading-platform-orchestration.git
cd trading-platform-orchestration

python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt

python -m pytest tests/test_gitroll_manifests.py -v
```

Six tests, all offline. This is the test selection the `Python Tests` job runs
on every pull request.

Then run the lint gate, which is the other half of CI:

```bash
python -m pip install pre-commit
pre-commit run --config .pre-commit/.pre-commit-config.yaml --all-files
```

### 2. Check the Compose wiring

`docker compose config` resolves variables and validates the service graph
without building or starting anything. The three secrets are declared required,
so the command needs values present in the environment — any placeholder is
fine, because `config` only interpolates them:

```bash
export POSTGRES_PASSWORD=placeholder
export JWT_SECRET=placeholder
export DATABASE_URL="postgres://trading_user:${POSTGRES_PASSWORD}@postgres:5432/trading_db?sslmode=disable"

docker compose config
```

The rendered output shows the absolute build-context paths Compose would use.
Those paths point at sibling directories that are not part of this repository,
which is exactly what the next section is about.

### 3. Preview the Kubernetes overlays

`deploy.sh` renders with `kubectl kustomize` first and only reaches for a
cluster afterwards. In dry-run mode it stops after rendering, so it needs
neither credentials nor a reachable cluster. Run it from `k8s/`, because the
overlay paths it builds are relative to the working directory:

```bash
cd k8s
DRY_RUN=true ./deploy.sh dev
DRY_RUN=true ./deploy.sh production
```

### Where getting started stops

`docker compose up`, `make up`, `make test`, and `./deploy.sh` without
`DRY_RUN=true` all need the component repositories, and those are not public.
Compose builds the API and the engine from sibling source directories, and the
Kubernetes manifests pin the engine to an image tag that only exists once you
have built it from the C++ component source. There is no public substitute, so
if you are reading this as a stranger to the project, those paths are closed —
stop at step 3.

[`docs/QUICKSTART.md`](docs/QUICKSTART.md) covers the same three public steps in
more detail. Its later sections — arranging the sibling workspace, starting the
stack, and curling the health endpoint — assume those non-public checkouts and
will not work without them.

## A worked example: the probe that must not be a health check

The clearest thing this repository contributes is not configuration, it is a
decision that configuration alone would not survive.

The Go API serves `/healthz`, and that endpoint deliberately degrades: it
returns `503` when the write-behind outbox passes half capacity or goes stale.
That is useful information for a load balancer and dangerous information for a
liveness probe. Point liveness at it and a burst of traffic makes Kubernetes
restart exactly the replicas that are working hardest — the ones holding the
most un-flushed writes in that in-memory outbox.

So the manifest splits the two probes. Liveness asks a cheaper question — is
anything listening on the port:

```yaml
livenessProbe:
  tcpSocket:
    port: 8000
  initialDelaySeconds: 15
  periodSeconds: 10
  failureThreshold: 5
readinessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 10
```

A saturated replica now leaves the service rotation and stays alive long enough
to drain. A dead one still gets restarted.

Nothing in a YAML file explains that, and a future edit that "simplifies" the
two probes into one looks harmless in review. So the reasoning is pinned by a
test instead:

```bash
python -m pytest tests/test_gitroll_manifests.py::test_backend_liveness_does_not_use_degrading_health_endpoint -v
```

```text
tests/test_gitroll_manifests.py::test_backend_liveness_does_not_use_degrading_health_endpoint PASSED [100%]

============================== 1 passed in 0.02s ===============================
```

The assertion compares the whole probe, not just its type, so changing the
endpoint, the delay, or the failure threshold all fail loudly. The engine makes
the same choice, which is why the rendered production overlay carries exactly
two TCP liveness probes:

```bash
cd k8s
kubectl kustomize overlays/production | grep -c 'tcpSocket'
```

```text
2
```

## Configuration reference

### Runtime inputs

Secrets are required inputs with no defaults, in both Compose and Kubernetes.
Compose fails fast when they are unset; `deploy.sh` refuses a non-preview
deployment and creates the Secret objects from the environment immediately
before applying. No Secret manifest is committed, and a manifest test enforces
that.

| Variable | Default | Purpose |
| --- | --- | --- |
| `POSTGRES_PASSWORD` | required | PostgreSQL password |
| `DATABASE_URL` | required | API database connection URL |
| `JWT_SECRET` | required | Application signing secret |
| `ENGINE_ADDR` | `hft-engine:50051` | Matching-engine gRPC endpoint |
| `ENGINE_ENABLED` | `true` | Enable the engine client |
| `WRITE_BEHIND` | `true` | Enable buffered database writes |
| `OUTBOX_BUFFER` | `10000` | Outbox channel capacity |
| `OUTBOX_BATCH` | `50` | Maximum write batch size |
| `OUTBOX_FLUSH` | `50ms` | Partial-batch flush interval |
| `OUTBOX_LAG_THRESHOLD` | `5s` | Health threshold for outbox lag |
| `LOG_LEVEL` | `info` | Logging level |
| `LOG_FORMAT` | `json` | Logging format |
| `APP_ENV` | `production` | Runtime environment selector |

### Ports

| Service | Port | Protocol | Defined in |
| --- | --- | --- | --- |
| Backend API | `8000` | HTTP and WebSocket | Compose and Kubernetes |
| Matching engine | `50051` | gRPC | Compose and Kubernetes |
| Matching engine | `9001` | UDP | Kubernetes only |
| PostgreSQL | `5432` | TCP | Compose and Kubernetes |
| Nginx ingress | `80` and `8080` | TCP, to listener `8080` | Kubernetes only |

### Environment differences

| Setting | `dev` overlay | `production` overlay |
| --- | --- | --- |
| Backend replicas | 1 | 4 |
| Backend memory limit | 128Mi | 512Mi |
| Backend CPU limit | 250m | 1000m |
| Engine memory limit | 512Mi | 1Gi |
| Engine image tag | `dev` | `2a722ff` |
| Image pull policy | `Never`, local images | `IfNotPresent` |
| Prometheus annotations | no | yes |

Both overlays also generate an `hft-config` ConfigMap carrying a per-environment
log level. No workload references it yet — the base kustomization marks that
generator as reserved for future use, and the API reads its settings from
`backend-config` instead. Render an overlay if you want to confirm which
ConfigMap a container actually consumes.

## Repository layout

```text
docker-compose.yml           # local multi-service composition
k8s/
├── base/                    # namespace, postgres, engine, backend, nginx
├── overlays/dev/            # 1 backend replica, local image tags
├── overlays/production/     # 4 backend replicas, pinned release tags
└── deploy.sh                # render, then optionally apply
tests/
├── test_gitroll_manifests.py  # active manifest regressions
└── integration_test.py        # legacy, see note below
scripts/                     # database bootstrap, image build, load generators
docs/
├── QUICKSTART.md            # local integration guide
├── RELEASE.md               # release checklist
├── PERFORMANCE.md           # load-test procedure and result format
└── gitroll-triage.md        # static-analysis findings and dispositions
```

`tests/integration_test.py` targets a historical Python API that no longer
exists in the platform. `pytest.ini` collects only `test_*.py`, so it is not
discovered; the active checks are the ones in `tests/test_gitroll_manifests.py`.

## Performance

**No benchmark result is retained in this repository.** There are no published
throughput, latency, fill, or profit-and-loss figures here, and the resource
limits and replica counts in the overlays are configuration choices, not
measurements. Treat any number in the manifests as a target, not a result.

[`docs/PERFORMANCE.md`](docs/PERFORMANCE.md) describes the load-generation
helpers in `scripts/` and what a run would have to record to be worth
publishing. Running them needs a live stack, which needs the non-public
components.

## Contributing

Changes are welcome on the public contract — the Compose file, the manifests,
the overlays, the tests, the scripts, and the docs.

1. Branch from `main`.
2. Make the change, and add or update a test in
   `tests/test_gitroll_manifests.py` when it encodes a rule that should not
   silently regress.
3. Run both CI gates locally:

   ```bash
   python -m pytest tests/test_gitroll_manifests.py -v
   pre-commit run --config .pre-commit/.pre-commit-config.yaml --all-files
   ```

4. Open a pull request against `main` and fill in the template.

Two things to know before you file an issue. Behavior that belongs to the Go or
C++ components cannot be fixed from here; what can be fixed here is how this
repository references and configures them. And vulnerabilities should not go in
a public issue — [SECURITY.md](SECURITY.md) has the private reporting path and
the scope boundary.

[`docs/RELEASE.md`](docs/RELEASE.md) is the checklist for publishing an
orchestration revision. This repository does not publish releases or deploy an
environment automatically.

## License

The orchestration files, tests, scripts, and documentation here are released
under the [MIT License](LICENSE). The component repositories are separate works
and are not covered by it.
