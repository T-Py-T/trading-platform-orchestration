"""Contract tests for backend ↔ engine Kubernetes wiring (offline YAML checks)."""

from test_gitroll_manifests import ROOT, load_documents, workloads


def backend_deployment() -> dict:
    return workloads("k8s/base/hft-backend.yaml")[0]


def backend_config() -> dict:
    documents = load_documents("k8s/base/hft-backend.yaml")
    return next(document for document in documents if document["kind"] == "ConfigMap")


def engine_deployment() -> dict:
    return workloads("k8s/base/hft-engine.yaml")[0]


def engine_service() -> dict:
    documents = load_documents("k8s/base/hft-engine.yaml")
    return next(document for document in documents if document["kind"] == "Service")


def test_backend_rolling_update_preserves_capacity() -> None:
    """Production rollouts should not take backends offline during surge."""
    strategy = backend_deployment()["spec"]["strategy"]
    assert strategy["type"] == "RollingUpdate"
    assert strategy["rollingUpdate"]["maxUnavailable"] == 0
    assert strategy["rollingUpdate"]["maxSurge"] >= 1


def test_backend_readiness_and_liveness_use_different_signals() -> None:
    """Readiness may fail under load while liveness keeps the pod running."""
    container = backend_deployment()["spec"]["template"]["spec"]["containers"][0]
    liveness = container["livenessProbe"]
    readiness = container["readinessProbe"]

    assert "tcpSocket" in liveness
    assert liveness["tcpSocket"]["port"] == 8000
    assert readiness["httpGet"]["path"] == "/healthz"
    assert readiness["httpGet"]["port"] == 8000


def test_backend_runtime_secrets_are_not_literal_values() -> None:
    """Database and JWT credentials must come from cluster secrets."""
    container = backend_deployment()["spec"]["template"]["spec"]["containers"][0]
    env_by_name = {item["name"]: item for item in container["env"]}

    for secret_name in ("DATABASE_URL", "JWT_SECRET"):
        env = env_by_name[secret_name]
        assert env["valueFrom"]["secretKeyRef"]["name"] == "backend-secrets"
        assert env["valueFrom"]["secretKeyRef"]["key"] == secret_name
        assert "value" not in env


def test_backend_points_at_engine_grpc_service() -> None:
    """The API server must target the engine Service DNS name and gRPC port."""
    config = backend_config()["data"]
    service = engine_service()

    grpc_port = next(
        port for port in service["spec"]["ports"] if port["name"] == "grpc"
    )
    assert config["ENGINE_ADDR"] == f"hft-engine:{grpc_port['port']}"
    assert config["ENGINE_ENABLED"] == "true"


def test_engine_exposes_grpc_and_udp_ports() -> None:
    """The trading engine must publish both gRPC and UDP listener ports."""
    service_ports = {port["name"]: port for port in engine_service()["spec"]["ports"]}
    container_ports = {
        port["name"]: port
        for port in engine_deployment()["spec"]["template"]["spec"]["containers"][0][
            "ports"
        ]
    }

    assert service_ports["grpc"]["port"] == 50051
    assert service_ports["udp"]["protocol"] == "UDP"
    assert container_ports["grpc"]["containerPort"] == 50051
    assert container_ports["udp"]["containerPort"] == 9001


def test_production_overlay_scales_backend_replicas() -> None:
    """Production overlay should request HA backend replica count."""
    import yaml

    overlay = yaml.safe_load(
        (ROOT / "k8s/overlays/production/kustomization.yaml").read_text(
            encoding="utf-8"
        )
    )
    replica_counts = {
        entry["name"]: entry["count"] for entry in overlay.get("replicas", [])
    }
    assert replica_counts["hft-backend"] == 4
