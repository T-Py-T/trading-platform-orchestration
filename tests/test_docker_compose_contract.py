"""Contract tests ensuring docker-compose wiring matches Kubernetes expectations."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def compose_services() -> dict:
    with (ROOT / "docker-compose.yml").open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data["services"]


def test_compose_stack_has_no_legacy_redis_service() -> None:
    """The Go backend replaced Redis; compose must not resurrect the old dependency."""
    services = compose_services()
    assert "redis" not in services


def test_backend_waits_for_postgres_and_engine_health() -> None:
    """API startup order must mirror production dependencies on data and matching."""
    backend = compose_services()["hft-backend"]
    depends_on = backend["depends_on"]
    assert depends_on["postgres"]["condition"] == "service_healthy"
    assert depends_on["hft-engine"]["condition"] == "service_healthy"


def test_backend_engine_address_matches_kubernetes_dns() -> None:
    """Compose ENGINE_ADDR should use the same host:port as the cluster ConfigMap."""
    backend_env = compose_services()["hft-backend"]["environment"]
    env_map = {
        item.split("=", 1)[0]: item.split("=", 1)[1]
        for item in backend_env
        if isinstance(item, str) and "=" in item
    }
    assert env_map["ENGINE_ENABLED"] == "true"
    assert env_map["ENGINE_ADDR"] == "hft-engine:50051"
