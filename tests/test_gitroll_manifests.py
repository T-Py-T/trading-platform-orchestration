"""Regression checks for the GitRoll infrastructure findings."""

import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKLOAD_MANIFESTS = (
    "k8s/base/hft-backend.yaml",
    "k8s/base/hft-engine.yaml",
    "k8s/base/nginx-ingress.yaml",
    "k8s/base/postgres.yaml",
    "k8s/base/postgres-sharded.yaml",
)


def load_documents(relative_path: str) -> list[dict]:
    """Load all non-empty Kubernetes documents from a repository file."""
    with (ROOT / relative_path).open(encoding="utf-8") as manifest:
        return [document for document in yaml.safe_load_all(manifest) if document]


def workloads(relative_path: str) -> list[dict]:
    """Return the pod-owning resources in a Kubernetes manifest."""
    return [
        document
        for document in load_documents(relative_path)
        if document.get("kind") in {"Deployment", "StatefulSet"}
    ]


def test_workloads_disable_tokens_and_bound_ephemeral_storage() -> None:
    """Every reported workload has least-privilege tokens and storage bounds."""
    checked = 0
    for relative_path in WORKLOAD_MANIFESTS:
        for workload in workloads(relative_path):
            checked += 1
            pod_spec = workload["spec"]["template"]["spec"]
            assert pod_spec["automountServiceAccountToken"] is False
            for container in pod_spec["containers"]:
                resources = container["resources"]
                assert resources["requests"]["ephemeral-storage"]
                assert resources["limits"]["ephemeral-storage"]

    assert checked == 7


def test_application_images_are_pinned() -> None:
    """Application workloads use auditable tags instead of floating latest."""
    backend = workloads("k8s/base/hft-backend.yaml")[0]
    engine = workloads("k8s/base/hft-engine.yaml")[0]

    assert backend["spec"]["template"]["spec"]["containers"][0]["image"].endswith(
        ":v0.1.0"
    )
    assert engine["spec"]["template"]["spec"]["containers"][0]["image"].endswith(
        ":2a722ff"
    )


def test_credentials_are_runtime_inputs() -> None:
    """Compose and Kubernetes sources contain no committed credential values."""
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "POSTGRES_PASSWORD=${POSTGRES_PASSWORD:?" in compose
    assert "DATABASE_URL=${DATABASE_URL:?" in compose
    assert "JWT_SECRET=${JWT_SECRET:?" in compose
    assert "trading_password" not in compose
    assert not (ROOT / "k8s/overlays/production/secrets.yaml").exists()

    for relative_path in ("k8s/base/postgres.yaml", "k8s/base/postgres-sharded.yaml"):
        assert all(
            document.get("kind") != "Secret"
            for document in load_documents(relative_path)
        )


def test_nginx_service_routes_to_the_configured_listener() -> None:
    """The public port targets the only port configured in nginx.conf."""
    documents = load_documents("k8s/base/nginx-ingress.yaml")
    service = next(document for document in documents if document["kind"] == "Service")
    http_port = next(
        port for port in service["spec"]["ports"] if port["name"] == "http"
    )
    assert http_port["targetPort"] == 8080


def test_backend_liveness_does_not_use_degrading_health_endpoint() -> None:
    """Load-driven /healthz failures must not restart an otherwise live API."""
    backend = workloads("k8s/base/hft-backend.yaml")[0]
    liveness = backend["spec"]["template"]["spec"]["containers"][0]["livenessProbe"]
    assert liveness == {
        "tcpSocket": {"port": 8000},
        "initialDelaySeconds": 15,
        "periodSeconds": 10,
        "failureThreshold": 5,
    }


def test_deploy_dry_run_does_not_contact_or_mutate_cluster(tmp_path: Path) -> None:
    """Preview mode renders locally without requiring credentials or a cluster."""
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    cluster_log = tmp_path / "cluster-calls.log"
    kubectl = mock_bin / "kubectl"
    kubectl.write_text(
        """#!/bin/bash
set -eu
case "$1" in
  version)
    exit 0
    ;;
  kustomize)
    printf '%s\n' 'apiVersion: v1' 'kind: ConfigMap' 'metadata:' '  name: preview'
    ;;
  get|create|apply|rollout|logs)
    printf '%s\n' "$*" >> "$KUBECTL_CLUSTER_LOG"
    exit 1
    ;;
  *)
    printf 'unexpected kubectl invocation: %s\n' "$*" >&2
    exit 2
    ;;
esac
""",
        encoding="utf-8",
    )
    kubectl.chmod(0o755)

    environment = os.environ.copy()
    environment.update(
        {
            "DRY_RUN": "true",
            "KUBECTL_CLUSTER_LOG": str(cluster_log),
            "PATH": f"{mock_bin}{os.pathsep}{environment['PATH']}",
        }
    )
    for secret_name in ("POSTGRES_PASSWORD", "DATABASE_URL", "JWT_SECRET"):
        environment.pop(secret_name, None)

    result = subprocess.run(
        [str(ROOT / "k8s/deploy.sh"), "production"],
        cwd=ROOT / "k8s",
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "DRY RUN MODE - Preview only" in result.stdout
    assert "name: preview" in result.stdout
    assert not cluster_log.exists(), cluster_log.read_text(encoding="utf-8")

    environment["DRY_RUN"] = "false"
    result = subprocess.run(
        [str(ROOT / "k8s/deploy.sh"), "production"],
        cwd=ROOT / "k8s",
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "POSTGRES_PASSWORD must be set for deployment" in result.stdout
    assert not cluster_log.exists(), cluster_log.read_text(encoding="utf-8")
