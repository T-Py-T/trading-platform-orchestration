"""Offline contract tests for the C++ engine Kubernetes manifest."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ENGINE_MANIFEST = ROOT / "k8s/base/hft-engine.yaml"


def load_documents() -> list[dict]:
    with ENGINE_MANIFEST.open(encoding="utf-8") as handle:
        return [doc for doc in yaml.safe_load_all(handle) if doc]


def test_engine_service_exposes_grpc_and_udp_ports() -> None:
    """Downstream clients rely on named gRPC and UDP listener ports."""
    service = next(doc for doc in load_documents() if doc["kind"] == "Service")
    ports = {entry["name"]: entry for entry in service["spec"]["ports"]}
    assert ports["grpc"]["port"] == 50051
    assert ports["grpc"]["targetPort"] == 50051
    assert ports["udp"]["port"] == 9001
    assert ports["udp"]["protocol"] == "UDP"


def test_engine_deployment_liveness_targets_grpc_socket() -> None:
    """Engine health checks must probe the gRPC listener, not an HTTP shim."""
    deployment = next(doc for doc in load_documents() if doc["kind"] == "Deployment")
    probe = deployment["spec"]["template"]["spec"]["containers"][0]["livenessProbe"]
    assert probe["tcpSocket"]["port"] == 50051
    assert probe["periodSeconds"] == 10
