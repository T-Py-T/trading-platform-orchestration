"""Source-level overlay checks that do not require the kustomize binary."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_kustomization(relative_path: str) -> dict:
    with (ROOT / relative_path).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def replica_count(kustomization: dict, name: str) -> int:
    for entry in kustomization.get("replicas", []):
        if entry["name"] == name:
            return entry["count"]
    raise KeyError(name)


def test_base_kustomization_lists_existing_manifest_files() -> None:
    """Broken resource paths would make every overlay build fail."""
    kustomization = load_kustomization("k8s/base/kustomization.yaml")
    for resource in kustomization["resources"]:
        assert (ROOT / "k8s/base" / resource).is_file()


def test_dev_overlay_scales_down_and_tags_development() -> None:
    """Development overlay should run minimal replicas with debug-oriented labels."""
    overlay = load_kustomization("k8s/overlays/dev/kustomization.yaml")
    assert replica_count(overlay, "hft-backend") == 1
    label_pairs = overlay["labels"][0]["pairs"]
    assert label_pairs["environment"] == "development"
    assert overlay["configMapGenerator"][0]["literals"][1] == 'LOG_LEVEL="debug"'


def test_production_overlay_scales_backend_and_enables_metrics_patch() -> None:
    """Production overlay must scale the API and annotate pods for Prometheus scraping."""
    overlay = load_kustomization("k8s/overlays/production/kustomization.yaml")
    assert replica_count(overlay, "hft-backend") == 4
    label_pairs = overlay["labels"][0]["pairs"]
    assert label_pairs["environment"] == "production"

    backend_patches = [
        patch
        for patch in overlay["patches"]
        if patch["target"]["kind"] == "Deployment" and patch["target"]["name"] == "hft-backend"
    ]
    prometheus_patch = next(
        patch for patch in backend_patches if "prometheus.io/scrape" in patch["patch"]
    )
    assert 'prometheus.io/scrape: "true"' in prometheus_patch["patch"]
