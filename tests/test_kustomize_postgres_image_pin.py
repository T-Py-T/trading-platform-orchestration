"""Regression: Kustomize must not replace the pinned Postgres 18 image."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
POSTGRES_MANIFEST = ROOT / "k8s/base/postgres.yaml"
KUSTOMIZATION = ROOT / "k8s/base/kustomization.yaml"
DEV_OVERLAY = ROOT / "k8s/overlays/dev"


def _pinned_postgres_image() -> str:
    documents = yaml.safe_load_all(POSTGRES_MANIFEST.read_text(encoding="utf-8"))
    statefulset = next(doc for doc in documents if doc.get("kind") == "StatefulSet")
    return statefulset["spec"]["template"]["spec"]["containers"][0]["image"]


def test_base_kustomization_does_not_override_postgres_image() -> None:
    """The base images transformer must not downgrade the StatefulSet pin."""
    kustomization = yaml.safe_load(KUSTOMIZATION.read_text(encoding="utf-8"))
    postgres_overrides = [
        entry
        for entry in kustomization.get("images", [])
        if entry.get("name") == "postgres"
    ]
    assert postgres_overrides == [], (
        "postgres image overrides belong in postgres.yaml (digest pin), not kustomization"
    )


def test_kustomize_dev_overlay_keeps_postgres_manifest_image() -> None:
    """Rendered dev manifests must keep the postgres.yaml image reference."""
    kustomize = shutil.which("kustomize")
    if kustomize is None:
        pytest_skip = __import__("pytest").skip
        pytest_skip("kustomize binary not on PATH")

    pinned = _pinned_postgres_image()
    rendered = subprocess.run(
        [kustomize, "build", str(DEV_OVERLAY)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert f"image: {pinned}" in rendered
    assert "image: postgres:16-alpine" not in rendered


def test_kustomize_dev_overlay_keeps_postgres_digest_pin() -> None:
    """Postgres must stay on the 18.x line with an immutable digest."""
    kustomize = os.environ.get("KUSTOMIZE") or shutil.which("kustomize")
    if kustomize is None:
        pytest_skip = __import__("pytest").skip
        pytest_skip("kustomize binary not on PATH")

    rendered = subprocess.run(
        [kustomize, "build", str(DEV_OVERLAY)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert "postgres:18" in rendered
    assert "@sha256:" in rendered
