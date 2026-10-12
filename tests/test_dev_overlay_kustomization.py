"""Development overlay expectations (k8s/overlays/dev/kustomization.yaml)."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEV_OVERLAY = ROOT / "k8s/overlays/dev/kustomization.yaml"


def load_dev_overlay() -> dict:
    with DEV_OVERLAY.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_dev_overlay_scales_backend_down_for_local_clusters() -> None:
    """Dev should run a single API replica with debug-friendly config."""
    overlay = load_dev_overlay()
    replica_counts = {
        entry["name"]: entry["count"] for entry in overlay.get("replicas", [])
    }
    assert replica_counts["hft-backend"] == 1
    assert replica_counts["postgres"] == 1

    literals = overlay["configMapGenerator"][0]["literals"]
    merged = {item.split("=")[0]: item.split("=", 1)[1].strip('"') for item in literals}
    assert merged["ENVIRONMENT"] == "development"
    assert merged["LOG_LEVEL"] == "debug"
    assert merged["APP_ENV"] == "development"


def test_dev_overlay_uses_local_image_tags_and_never_pull_policy() -> None:
    """Engine images should resolve to dev tags and skip registry pulls."""
    overlay = load_dev_overlay()
    images = {entry["name"]: entry["newTag"] for entry in overlay.get("images", [])}
    assert images["hft-engine"] == "dev"
    assert images["ghcr.io/t-py-t/ml-trading-app-go-server"] == "v0.1.0"

    patch_targets = {
        (patch["target"]["kind"], patch["target"]["name"])
        for patch in overlay.get("patches", [])
    }
    assert ("Deployment", "hft-backend") in patch_targets
    assert ("Deployment", "hft-engine") in patch_targets

    backend_pull_patch = next(
        patch
        for patch in overlay["patches"]
        if patch["target"] == {"kind": "Deployment", "name": "hft-backend"}
        and "imagePullPolicy" in patch["patch"]
    )
    assert 'value: Never' in backend_pull_patch["patch"]
