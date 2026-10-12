"""Kustomize render smoke tests for deployment-critical overlays."""

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
OVERLAYS = (
    "k8s/base",
    "k8s/overlays/dev",
    "k8s/overlays/production",
)


def kustomize_binary() -> str:
    binary = shutil.which("kustomize")
    if binary:
        return binary

    kubectl = shutil.which("kubectl")
    if kubectl:
        return f"{kubectl} kustomize"

    pytest.skip("kustomize or kubectl is not installed")


def kustomize_build(relative_path: str) -> list[dict]:
    binary = kustomize_binary()
    if binary.endswith("kustomize"):
        command = [binary, "build", str(ROOT / relative_path)]
    else:
        kubectl, subcommand = binary.split()
        command = [kubectl, subcommand, str(ROOT / relative_path)]

    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return [document for document in yaml.safe_load_all(result.stdout) if document]


def workload_documents(relative_path: str) -> list[dict]:
    return [
        document
        for document in kustomize_build(relative_path)
        if document.get("kind") in {"Deployment", "StatefulSet"}
    ]


@pytest.mark.parametrize("relative_path", OVERLAYS)
def test_kustomize_build_includes_core_workloads(relative_path: str) -> None:
    """Every overlay should render backend, engine, and Postgres workloads."""
    names = {document["metadata"]["name"] for document in workload_documents(relative_path)}
    assert {"hft-backend", "hft-engine", "postgres"}.issubset(names)


def test_production_render_sets_backend_replica_count() -> None:
    """Production overlay must scale the Go API to four replicas."""
    backend = next(
        document
        for document in workload_documents("k8s/overlays/production")
        if document["metadata"]["name"] == "hft-backend"
    )
    assert backend["spec"]["replicas"] == 4


def test_dev_render_uses_local_image_pull_policy() -> None:
    """Development overlay should never pull images from a remote registry."""
    for workload_name in ("hft-backend", "hft-engine"):
        workload = next(
            document
            for document in workload_documents("k8s/overlays/dev")
            if document["metadata"]["name"] == workload_name
        )
        policy = workload["spec"]["template"]["spec"]["containers"][0]["imagePullPolicy"]
        assert policy == "Never"
