"""Additional deploy.sh safety checks beyond the GitRoll dry-run regression."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_deploy(
    environment: str,
    *,
    dry_run: bool | None = None,
    kubectl_path: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    mock_bin = kubectl_path.parent if kubectl_path else None
    environment_vars = os.environ.copy()
    if extra_env:
        environment_vars.update(extra_env)
    if dry_run is not None:
        environment_vars["DRY_RUN"] = "true" if dry_run else "false"
    if mock_bin is not None:
        environment_vars["PATH"] = f"{mock_bin}{os.pathsep}{environment_vars['PATH']}"

    return subprocess.run(
        [str(ROOT / "k8s/deploy.sh"), environment],
        cwd=ROOT / "k8s",
        env=environment_vars,
        check=False,
        capture_output=True,
        text=True,
    )


def write_mock_kubectl(mock_bin: Path) -> Path:
    mock_bin.mkdir(parents=True, exist_ok=True)
    kubectl = mock_bin / "kubectl"
    kubectl.write_text(
        """#!/bin/bash
set -eu
case "$1" in
  version)
    exit 0
    ;;
  kustomize)
    printf '%s\\n' 'apiVersion: v1' 'kind: ConfigMap' 'metadata:' '  name: preview'
    ;;
  *)
    printf 'unexpected kubectl invocation: %s\\n' "$*" >&2
    exit 2
    ;;
esac
""",
        encoding="utf-8",
    )
    kubectl.chmod(0o755)
    return kubectl


def test_deploy_rejects_unknown_environment() -> None:
    """Only dev and production overlays are supported entry points."""
    result = run_deploy("staging")
    assert result.returncode == 1
    assert "Invalid environment 'staging'" in result.stdout


def test_deploy_dev_dry_run_renders_without_secrets(tmp_path: Path) -> None:
    """Development preview should succeed without runtime secret injection."""
    kubectl = write_mock_kubectl(tmp_path / "bin")
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {"POSTGRES_PASSWORD", "DATABASE_URL", "JWT_SECRET"}
    }

    result = subprocess.run(
        [str(ROOT / "k8s/deploy.sh"), "dev"],
        cwd=ROOT / "k8s",
        env={
            **environment,
            "DRY_RUN": "true",
            "PATH": f"{kubectl.parent}{os.pathsep}{environment['PATH']}",
        },
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Environment: dev" in result.stdout
    assert "DRY RUN MODE - Preview only" in result.stdout
