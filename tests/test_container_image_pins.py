"""Regression checks for digest-pinned infrastructure images."""

import re
import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
POSTGRES_DIGEST = (
    "postgres:18.6-alpine@sha256:d8703cd7fba306b9fec9268ecedfa8a966846c053036a60e3635791957eb2f66"
)
NGINX_DIGEST = (
    "nginx:1.31.6-alpine@sha256:0530961ff0592b58c10f767535cc0abdfccf9e389ff7cc90f87320c1bc7e8506"
)
IMAGE_RE = re.compile(r"^.+@sha256:[a-f0-9]{64}$")


def _postgres_images() -> list[str]:
    paths = [
        ROOT / "docker-compose.yml",
        ROOT / "k8s" / "base" / "postgres.yaml",
        ROOT / "k8s" / "base" / "postgres-sharded.yaml",
    ]
    images: list[str] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if "image:" in line and "postgres:" in line:
                images.append(line.split("image:", 1)[1].strip())
    return images


def test_postgres_and_nginx_use_current_digest_pins() -> None:
    """Third-party base images are pinned to audited digests."""
    assert all(image == POSTGRES_DIGEST for image in _postgres_images())
    nginx_line = next(
        line
        for line in (ROOT / "k8s" / "base" / "nginx-ingress.yaml")
        .read_text(encoding="utf-8")
        .splitlines()
        if "image:" in line and "nginx:" in line
    )
    assert nginx_line.split("image:", 1)[1].strip() == NGINX_DIGEST


def test_kustomize_overlays_keep_postgres_digest_pin() -> None:
    """Kustomize must not rewrite Postgres to a floating tag."""
    if shutil.which("kustomize") is None:
        return

    for overlay in ("dev", "production"):
        rendered = subprocess.run(
            ["kustomize", "build", str(ROOT / "k8s" / "overlays" / overlay)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        postgres_images = [
            document["spec"]["template"]["spec"]["containers"][0]["image"]
            for document in yaml.safe_load_all(rendered)
            if document
            and document.get("kind") == "StatefulSet"
            and document.get("metadata", {}).get("name") == "postgres"
        ]
        assert postgres_images == [POSTGRES_DIGEST]


def test_list_digest_pinned_images_script_matches_manifests() -> None:
    """CI Trivy step scans every digest-pinned image in base manifests."""
    script = ROOT / "scripts" / "list_digest_pinned_images.py"
    listed = subprocess.run(
        ["python3", str(script)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert listed == sorted({POSTGRES_DIGEST, NGINX_DIGEST})
    assert all(IMAGE_RE.match(image) for image in listed)
