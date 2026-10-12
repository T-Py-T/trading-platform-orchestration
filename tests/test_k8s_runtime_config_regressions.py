"""Regression tests for Kubernetes runtime configuration bugs."""

import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_documents(relative_path: str) -> list[dict]:
    with (ROOT / relative_path).open(encoding="utf-8") as handle:
        return [document for document in yaml.safe_load_all(handle) if document]


def backend_config_from_base() -> dict[str, str]:
    config_map = next(
        document
        for document in load_documents("k8s/base/hft-backend.yaml")
        if document.get("kind") == "ConfigMap"
        and document.get("metadata", {}).get("name") == "backend-config"
    )
    return config_map["data"]


def production_backend_config_patch() -> str:
    overlay = yaml.safe_load(
        (ROOT / "k8s/overlays/production/kustomization.yaml").read_text(encoding="utf-8")
    )
    for patch in overlay.get("patches", []):
        target = patch.get("target", {})
        if target.get("kind") == "ConfigMap" and target.get("name") == "backend-config":
            return patch["patch"]
    raise AssertionError("production overlay must patch backend-config runtime values")


def test_backend_config_base_defaults_match_dev_overlay() -> None:
    """Dev overlay does not patch backend-config; base must not ship production env."""
    data = backend_config_from_base()
    assert data["APP_ENV"] == "development"
    assert data["LOG_LEVEL"] == "debug"


def test_production_overlay_patches_backend_config_runtime() -> None:
    """Production must explicitly promote backend-config to production logging."""
    patch = production_backend_config_patch()
    assert 'path: /data/APP_ENV' in patch
    assert 'value: "production"' in patch
    assert 'path: /data/LOG_LEVEL' in patch
    assert 'value: "info"' in patch


def test_hft_engine_deployment_has_grpc_readiness_probe() -> None:
    """Rollouts should wait for the gRPC listener before marking the engine ready."""
    deployment = next(
        document
        for document in load_documents("k8s/base/hft-engine.yaml")
        if document["kind"] == "Deployment"
    )
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    readiness = container["readinessProbe"]
    assert readiness["tcpSocket"]["port"] == 50051
    assert readiness["periodSeconds"] == 5


def test_kustomize_renders_expected_backend_config_when_available() -> None:
    """Optional render check when the kustomize CLI is installed."""
    binary = shutil.which("kustomize")
    if binary is None and Path("/tmp/kustomize").is_file():
        binary = "/tmp/kustomize"
    if binary is None:
        return

    for overlay, app_env, log_level in (
        ("dev", "development", "debug"),
        ("production", "production", "info"),
    ):
        result = subprocess.run(
            [binary, "build", str(ROOT / "k8s" / "overlays" / overlay)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        documents = [
            document for document in yaml.safe_load_all(result.stdout) if document
        ]
        config_map = next(
            document
            for document in documents
            if document.get("kind") == "ConfigMap"
            and document.get("metadata", {}).get("name") == "backend-config"
        )
        assert config_map["data"]["APP_ENV"] == app_env
        assert config_map["data"]["LOG_LEVEL"] == log_level
