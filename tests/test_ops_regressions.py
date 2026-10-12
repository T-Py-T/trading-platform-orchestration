"""Regression tests for deploy and image-build ops scripts."""

import os
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def write_kustomize_kubectl(mock_bin: Path) -> Path:
    mock_bin.mkdir(parents=True, exist_ok=True)
    kubectl = mock_bin / "kubectl"
    kubectl.write_text(
        f"""#!/bin/bash
set -eu
case "$1" in
  version)
    exit 0
    ;;
  kustomize)
    /tmp/kustomize build "$2" || exit 1
    ;;
  get|create|apply|rollout|logs)
    exit 1
    ;;
  *)
    exit 2
    ;;
esac
""",
        encoding="utf-8",
    )
    kubectl.chmod(0o755)
    return kubectl


def test_deploy_dry_run_works_from_repository_root(tmp_path: Path) -> None:
    """deploy.sh must resolve overlays relative to k8s/, not the caller's cwd."""
    kubectl = write_kustomize_kubectl(tmp_path / "bin")
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {"POSTGRES_PASSWORD", "DATABASE_URL", "JWT_SECRET"}
    }
    environment["DRY_RUN"] = "true"
    environment["PATH"] = f"{kubectl.parent}{os.pathsep}{environment['PATH']}"

    result = subprocess.run(
        [str(ROOT / "k8s/deploy.sh"), "dev"],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "DRY RUN MODE - Preview only" in result.stdout
    assert "hft-backend" in result.stdout


def test_deploy_waits_only_for_deployments_that_exist() -> None:
    """Rollout wait list must not reference removed Redis workloads."""
    deploy_script = (ROOT / "k8s/deploy.sh").read_text(encoding="utf-8")
    match = re.search(r'DEPLOYMENTS=\(([^)]*)\)', deploy_script)
    assert match is not None
    deployments = match.group(1)
    assert "redis" not in deployments


def test_build_docker_images_matches_compose_backend() -> None:
    """The build script must target the same Go backend image as docker-compose."""
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    backend_build = compose["services"]["hft-backend"]["build"]
    assert backend_build["context"].endswith("ml-trading-app-go")
    assert backend_build["dockerfile"] == "Dockerfile.server"

    build_script = (ROOT / "scripts/build-docker-images.sh").read_text(encoding="utf-8")
    assert "ml-trading-app-go" in build_script
    assert "Dockerfile.server" in build_script
    assert "ml-trading-app-py" not in build_script
