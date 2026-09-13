# Local integration guide

This guide validates the public orchestration files and, when the component
repositories are available, starts the complete trading-platform stack.

## Requirements

- Python 3.11 or newer
- Docker with Compose v2
- `kubectl` for rendering Kubernetes overlays
- sibling checkouts of `ml-trading-app-go` and `ml-trading-app-cpp` for a full
  Compose build

## Validate the public repository

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt pre-commit
python -m pytest tests/test_gitroll_manifests.py -v
pre-commit run --config .pre-commit/.pre-commit-config.yaml --all-files
```

Preview both Kubernetes overlays without contacting a cluster:

```bash
DRY_RUN=true ./k8s/deploy.sh dev
DRY_RUN=true ./k8s/deploy.sh production
```

## Arrange the full workspace

The Compose file builds the API and engine from sibling directories:

```text
workspace/
├── trading-platform-orchestration/
├── ml-trading-app-go/
└── ml-trading-app-cpp/
```

Confirm that `docker compose config` resolves both build contexts before
starting services.

## Start the stack

Create ephemeral development credentials in the current shell:

```bash
export POSTGRES_PASSWORD="$(openssl rand -hex 24)"
export JWT_SECRET="$(openssl rand -hex 32)"
export DATABASE_URL="postgres://trading_user:${POSTGRES_PASSWORD}@postgres:5432/trading_db?sslmode=disable"

docker compose config
docker compose up -d --build
docker compose ps
curl http://localhost:8000/healthz
```

Do not commit these values or place production credentials in a repository
`.env` file.

## Inspect and stop

```bash
docker compose logs --tail=200
docker compose down
```

`docker compose down` preserves the PostgreSQL volume. Add `--volumes` only
when you intentionally want to delete local database state.

## Kubernetes preview

The deployment helper requires credentials only for a real apply. Use dry-run
mode first:

```bash
DRY_RUN=true ./k8s/deploy.sh production
```

See [`k8s/README.md`](../k8s/README.md) for image, secret, deployment, and
cleanup details.
