# Trading Platform Orchestration

Compose and Kubernetes orchestration for a componentized trading platform. The
repository defines how the Go API/TUI, C++ matching engine, and PostgreSQL
services are configured, connected, health-checked, and deployed.

The Go and C++ implementations are maintained in private component
repositories. This repository contains their integration contract: image and
build references, ports, environment variables, probes, resource limits,
deployment overlays, manifest tests, and operator notes.

## Architecture

```text
┌───────────────────────────────────────────────────────────┐
│ Compose and Kubernetes orchestration                      │
│ configuration · service wiring · probes · resource limits │
└───────────────┬───────────────────┬───────────────────────┘
                │                   │
        HTTP / WebSocket          gRPC
                │                   │
       ┌────────▼────────┐   ┌──────▼─────────┐
       │ Go API and TUI  │   │ C++ engine    │
       └────────┬────────┘   └────────────────┘
                │
       ┌────────▼────────┐
       │ PostgreSQL      │
       └─────────────────┘
```

| Component | Defined here |
| --- | --- |
| Orchestration | Compose file, Kubernetes bases and overlays, runtime inputs, and tests |
| Go API/TUI | Build context or pinned image, service configuration, HTTP/WebSocket port, and health probe |
| C++ engine | Build context or pinned image, gRPC address, resources, and health probe |
| PostgreSQL | Official image, persistent storage, credentials, and connection URL |

## Repository layout

```text
docker-compose.yml        # local multi-service composition
k8s/
├── base/                 # shared Kubernetes resources
└── overlays/             # development and production settings
tests/                    # manifest and configuration regressions
scripts/                  # setup and load-generation helpers
docs/
├── QUICKSTART.md         # development workflow
├── RELEASE.md            # release process
└── PERFORMANCE.md        # load-test procedure and result format
```

## Validate the public configuration

Create a local environment and run the active manifest tests:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt pre-commit

python -m pytest tests/test_gitroll_manifests.py -v
pre-commit run --config .pre-commit/.pre-commit-config.yaml --all-files
```

Render the Kubernetes overlays without applying them:

```bash
cd k8s
DRY_RUN=true ./deploy.sh dev
DRY_RUN=true ./deploy.sh production
```

These commands check the files in this repository. Starting the complete
platform additionally requires access to the component source or published
component images.

## Run the full stack

Place the three repositories next to one another so the Compose build contexts
resolve:

```text
workspace/
├── trading-platform-orchestration/
├── ml-trading-app-go/
└── ml-trading-app-cpp/
```

From `trading-platform-orchestration/`, create runtime credentials and start
the composition:

```bash
export POSTGRES_PASSWORD="$(openssl rand -hex 24)"
export JWT_SECRET="$(openssl rand -hex 32)"
export DATABASE_URL="postgres://trading_user:${POSTGRES_PASSWORD}@postgres:5432/trading_db?sslmode=disable"

docker-compose config
docker-compose up -d
docker-compose ps
curl http://localhost:8000/healthz
```

Secrets are required runtime inputs and must not be committed to the repository.

## Configuration

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
| `LOG_FORMAT` | `text` | Logging format |
| `APP_ENV` | `development` | Runtime environment selector |

## Ports

| Service | Port | Protocol |
| --- | --- | --- |
| Backend API | `8000` | HTTP and WebSocket |
| Matching engine | `50051` | gRPC |
| PostgreSQL | `5432` | TCP |

## Troubleshooting

If Compose cannot build a component, confirm both sibling source directories
exist and inspect the resolved build contexts:

```bash
docker-compose config
```

If services start but do not become healthy:

```bash
docker-compose ps
docker-compose logs
```

For Kubernetes configuration failures, render the chosen overlay first and
then rerun the manifest tests:

```bash
cd k8s
DRY_RUN=true ./deploy.sh dev
cd ..
python -m pytest tests/test_gitroll_manifests.py -v
```

`tests/integration_test.py` targets an older Python API and is excluded by
`pytest.ini`. The active checks are in `tests/test_gitroll_manifests.py`.

## License

The orchestration, tests, scripts, and documentation in this repository are
available under the [MIT License](LICENSE). The private Go and C++ component
repositories are separate works and are not covered by this license.
