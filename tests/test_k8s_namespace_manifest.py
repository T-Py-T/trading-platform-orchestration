"""Offline checks for the cluster namespace manifest."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE_PATH = ROOT / "k8s/base/namespace.yaml"


def load_namespace() -> dict:
    with NAMESPACE_PATH.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    assert isinstance(document, dict)
    return document


def test_namespace_manifest_declares_hft_trading() -> None:
    """The platform namespace name must match kustomization namespace fields."""
    document = load_namespace()
    assert document["apiVersion"] == "v1"
    assert document["kind"] == "Namespace"
    assert document["metadata"]["name"] == "hft-trading"


def test_namespace_labels_match_metadata_name() -> None:
    """Label selectors and documentation often key off the name label."""
    document = load_namespace()
    labels = document["metadata"]["labels"]
    assert labels["name"] == document["metadata"]["name"]
