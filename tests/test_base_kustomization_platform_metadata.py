"""Source-level checks for k8s/base/kustomization.yaml (no kustomize binary)."""

from pathlib import Path

import yaml

from test_gitroll_manifests import ROOT

BASE_KUSTOMIZATION = ROOT / "k8s/base/kustomization.yaml"


def load_base_kustomization() -> dict:
    with BASE_KUSTOMIZATION.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_base_resources_exclude_optional_sharded_postgres() -> None:
    """The default bundle ships single-node Postgres; sharding is a separate manifest."""
    resources = load_base_kustomization()["resources"]
    assert "postgres-sharded.yaml" not in resources
    assert "postgres.yaml" in resources


def test_base_applies_platform_labels_and_managed_by_annotation() -> None:
    """All rendered objects should inherit consistent Kubernetes recommended labels."""
    kustomization = load_base_kustomization()
    label_pairs = kustomization["labels"][0]["pairs"]
    assert label_pairs["app.kubernetes.io/name"] == "hft-trading"
    assert label_pairs["app.kubernetes.io/part-of"] == "hft-trading-platform"
    assert kustomization["commonAnnotations"]["app.kubernetes.io/managed-by"] == "kustomize"
    assert kustomization["namespace"] == "hft-trading"


def test_base_image_transforms_pin_application_tags() -> None:
    """Kustomize image rewrites must keep engine and Go API on auditable tags."""
    images = {entry["name"]: entry for entry in load_base_kustomization()["images"]}
    assert images["hft-engine"]["newTag"] == "2a722ff"
    assert images["ghcr.io/t-py-t/ml-trading-app-go-server"]["newTag"] == "v0.1.0"
    assert images["postgres"]["newTag"] == "16-alpine"


def test_base_replica_overrides_match_manifest_defaults() -> None:
    """Replica counts in kustomization should mirror Deployment/StatefulSet specs."""
    counts = {
        entry["name"]: entry["count"] for entry in load_base_kustomization()["replicas"]
    }
    assert counts == {"hft-backend": 2, "hft-engine": 1, "postgres": 1}
