# Kubernetes Deployment

## Quick Start

```bash
# Supply secrets at runtime. Use a secret manager in production.
export POSTGRES_PASSWORD="$(openssl rand -hex 24)"
export JWT_SECRET="$(openssl rand -hex 32)"
export DATABASE_URL="postgres://trading_user:${POSTGRES_PASSWORD}@postgres:5432/trading_db?sslmode=disable"

# Development (1 replica, debug logging)
./deploy.sh dev

# Production (4 replicas, info logging)
./deploy.sh production
```

## Environments

| Setting | Dev | Production |
| ------- | --- | ---------- |
| Backend Replicas | 1 | 4 |
| Log Level | DEBUG | INFO |
| Memory | 128Mi | 512Mi |
| CPU | 250m | 1000m |

## Verify

```bash
kubectl get all -n hft-trading
kubectl logs -f deployment/hft-backend -n hft-trading
kubectl port-forward svc/nginx-ingress 8080:80 -n hft-trading
curl http://localhost:8080/healthz   # outbox stats included in payload
```

## Scale

```bash
# Edit overlays/production/kustomization.yaml
# Change replicas: hft-backend -> count: 8
./deploy.sh production
```

## Image versions

The base and production manifests pin the backend from
[ml-trading-app-go](https://github.com/T-Py-T/ml-trading-app-go) to its published
`v0.1.0` release. They pin the C++ engine to source revision `2a722ff`; build
and tag that revision as `hft-trading-app-hft-engine:2a722ff` before deployment.
The development overlay instead expects locally loaded
`hft-trading-app-hft-engine:dev` and backend `v0.1.0` images and disables image
pulling for both workloads.

## Secrets

No Kubernetes Secret manifests are committed. For a non-preview deployment,
`deploy.sh` requires `POSTGRES_PASSWORD`, `DATABASE_URL`, and `JWT_SECRET`, then
creates the `postgres-secret` and `backend-secrets` objects immediately before
applying the workloads. `DRY_RUN=true` only renders a local preview and does not
require credentials or contact a cluster. Production operators should source those
variables from their secret manager. The optional sharded PostgreSQL manifest expects
`postgres-shard-0-secret` through `postgres-shard-2-secret` to be provisioned
out of band.

## Cleanup

```bash
kubectl delete namespace hft-trading
```

## Directory Structure

```text
k8s/
├── base/                    # Core manifests (postgres + C++ engine + Go backend + nginx)
├── overlays/
│   ├── dev/                # Development config (1 backend replica, debug logging)
│   └── production/         # Production config (4 backend replicas, info logging)
└── deploy.sh              # Deployment script
```
