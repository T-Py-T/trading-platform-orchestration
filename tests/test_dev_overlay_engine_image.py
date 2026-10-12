"""Dev overlay must apply the dev image tag after base image renames."""

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEV_OVERLAY = ROOT / "k8s" / "overlays" / "dev"


def _kustomize_build() -> list[dict]:
    binary = shutil.which("kustomize")
    if not binary:
        kubectl = shutil.which("kubectl")
        if not kubectl:
            pytest.skip("kustomize or kubectl is not installed")
        command = [kubectl, "kustomize", str(DEV_OVERLAY)]
    else:
        command = [binary, "build", str(DEV_OVERLAY)]

    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


def test_dev_overlay_renders_engine_with_dev_tag() -> None:
    engine = next(
        doc
        for doc in _kustomize_build()
        if doc.get("kind") == "Deployment" and doc["metadata"]["name"] == "hft-engine"
    )
    image = engine["spec"]["template"]["spec"]["containers"][0]["image"]
    assert image == "hft-trading-app-hft-engine:dev"
