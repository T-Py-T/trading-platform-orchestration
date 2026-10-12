"""Docker Compose runtime wiring aligned with the Kubernetes Go backend."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def compose() -> dict:
    with (ROOT / "docker-compose.yml").open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def env_entries(service: dict) -> dict[str, str]:
    raw = service.get("environment", [])
    result: dict[str, str] = {}
    for item in raw:
        if isinstance(item, str) and "=" in item:
            key, value = item.split("=", 1)
            result[key] = value
    return result


def test_backend_enables_write_behind_and_engine_integration() -> None:
    """Local stack must exercise the same ledger/outbox path as production."""
    backend = compose()["services"]["hft-backend"]
    env = env_entries(backend)
    assert env["WRITE_BEHIND"] == "true"
    assert env["ENGINE_ENABLED"] == "true"
    assert env["ENGINE_ADDR"] == "hft-engine:50051"
    assert env["HTTP_ADDR"] == ":8000"


def test_required_secrets_use_shell_parameter_expansion() -> None:
    """Compose must fail fast when credentials are not provided."""
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for key in ("POSTGRES_PASSWORD", "DATABASE_URL", "JWT_SECRET"):
        assert f"${{{key}:?" in text


def test_backend_healthcheck_targets_healthz_not_legacy_health() -> None:
    """Health checks should hit the Go server's load-aware readiness endpoint."""
    health = compose()["services"]["hft-backend"]["healthcheck"]["test"]
    joined = " ".join(health) if isinstance(health, list) else health
    assert "/healthz" in joined
    assert "/health" not in joined.replace("/healthz", "")


def test_engine_builds_from_cpp_sibling_repository() -> None:
    """Compose documents the expected monorepo layout for the matching engine."""
    engine = compose()["services"]["hft-engine"]["build"]
    assert engine["context"] == "../ml-trading-app-cpp"
    assert engine["dockerfile"] == "Dockerfile.prod"
