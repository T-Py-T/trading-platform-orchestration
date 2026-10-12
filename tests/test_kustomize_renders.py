"""Ensure Kustomize output preserves security pins from the base manifests."""

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
KUSTOMIZE_PATHS = (
    "k8s/base",
    "k8s/overlays/dev",
    "k8s/overlays/production",
)


def postgres_image_from_base_manifest() -> str:
    """Return the digest-pinned Postgres image from the base StatefulSet."""
    with (ROOT / "k8s/base/postgres.yaml").open(encoding="utf-8") as manifest:
        for document in yaml.safe_load_all(manifest):
            if document.get("kind") == "StatefulSet":
                return document["spec"]["template"]["spec"]["containers"][0]["image"]
    raise AssertionError(
        "postgres StatefulSet image not found in k8s/base/postgres.yaml"
    )


def kustomize_build(relative_path: str) -> list[dict]:
    """Render a Kustomize overlay and return parsed Kubernetes documents."""
    kustomize = shutil.which("kustomize")
    if kustomize is None:
        pytest.skip("kustomize is not installed")

    result = subprocess.run(
        [kustomize, "build", str(ROOT / relative_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return [document for document in yaml.safe_load_all(result.stdout) if document]


def container_images(relative_path: str) -> list[str]:
    """Collect container image references from a rendered overlay."""
    images: list[str] = []
    for document in kustomize_build(relative_path):
        spec = document.get("spec", {})
        template = spec.get("template", {})
        pod_spec = template.get("spec", {})
        for container in pod_spec.get("containers", []):
            image = container.get("image")
            if image:
                images.append(image)
    return images


@pytest.mark.parametrize("relative_path", KUSTOMIZE_PATHS)
def test_postgres_image_stays_digest_pinned(relative_path: str) -> None:
    """Kustomize must not downgrade Postgres to an unpinned major tag."""
    expected = postgres_image_from_base_manifest()
    assert expected in container_images(relative_path)


def test_dev_overlay_uses_development_engine_tag() -> None:
    """The development overlay should tag the engine image for local builds."""
    images = container_images("k8s/overlays/dev")
    assert any(image.endswith("hft-trading-app-hft-engine:dev") for image in images)
