"""Source-level checks for the production Kustomize overlay."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OVERLAY_PATH = ROOT / "k8s/overlays/production/kustomization.yaml"


def load_overlay() -> dict:
    with OVERLAY_PATH.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    assert isinstance(document, dict)
    return document


def test_production_overlay_pins_release_image_tags() -> None:
    """Production must not inherit floating development engine tags."""
    overlay = load_overlay()
    images = {entry["name"]: entry for entry in overlay["images"]}
    assert images["hft-engine"]["newTag"] == "2a722ff"
    assert images["ghcr.io/t-py-t/ml-trading-app-go-server"]["newTag"] == "v0.1.0"


def test_production_overlay_merges_runtime_config_literals() -> None:
    """Merged config map literals drive environment-aware logging and app env."""
    overlay = load_overlay()
    literals = overlay["configMapGenerator"][0]["literals"]
    merged = {line.split("=", 1)[0]: line.split("=", 1)[1] for line in literals}
    assert merged["ENVIRONMENT"] == '"production"'
    assert merged["LOG_LEVEL"] == '"info"'
    assert merged["APP_ENV"] == '"production"'
    assert overlay["configMapGenerator"][0]["behavior"] == "merge"
