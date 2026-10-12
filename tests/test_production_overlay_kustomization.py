"""Production overlay HA and observability settings."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PROD_OVERLAY = ROOT / "k8s/overlays/production/kustomization.yaml"


def load_production_overlay() -> dict:
    with PROD_OVERLAY.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_production_overlay_scales_backend_for_ha() -> None:
    """Production should run four API replicas with info-level logging."""
    overlay = load_production_overlay()
    replica_counts = {
        entry["name"]: entry["count"] for entry in overlay.get("replicas", [])
    }
    assert replica_counts["hft-backend"] == 4

    literals = overlay["configMapGenerator"][0]["literals"]
    merged = {item.split("=")[0]: item.split("=", 1)[1].strip('"') for item in literals}
    assert merged["ENVIRONMENT"] == "production"
    assert merged["LOG_LEVEL"] == "info"
    assert merged["APP_ENV"] == "production"


def test_production_overlay_enables_prometheus_scrape_on_backend() -> None:
    """Metrics should be discoverable without editing the base Deployment."""
    overlay = load_production_overlay()
    prom_patch = next(
        patch
        for patch in overlay["patches"]
        if patch["target"] == {"kind": "Deployment", "name": "hft-backend"}
        and "prometheus.io/scrape" in patch["patch"]
    )
    assert 'prometheus.io/scrape: "true"' in prom_patch["patch"]
    assert 'prometheus.io/port: "8000"' in prom_patch["patch"]
    assert 'prometheus.io/path: "/metrics"' in prom_patch["patch"]
