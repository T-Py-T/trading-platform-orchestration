"""Go API Deployment service exposure and rollout safety (not ConfigMap literals)."""

from test_gitroll_manifests import load_documents, workloads


def backend_service() -> dict:
    documents = load_documents("k8s/base/hft-backend.yaml")
    return next(document for document in documents if document["kind"] == "Service")


def backend_deployment() -> dict:
    return workloads("k8s/base/hft-backend.yaml")[0]


def test_backend_service_is_cluster_ip_on_port_8000() -> None:
    """In-cluster consumers should reach the API on port 8000."""
    service = backend_service()
    assert service["spec"]["type"] == "ClusterIP"
    port = service["spec"]["ports"][0]
    assert port["port"] == 8000
    assert port["targetPort"] == 8000
    assert service["spec"]["selector"]["app"] == "hft-backend"


def test_backend_rolling_update_keeps_capacity_during_rollouts() -> None:
    """maxUnavailable 0 prevents draining all API pods during image upgrades."""
    deployment = backend_deployment()
    strategy = deployment["spec"]["strategy"]["rollingUpdate"]
    assert deployment["spec"]["strategy"]["type"] == "RollingUpdate"
    assert strategy["maxSurge"] == 1
    assert strategy["maxUnavailable"] == 0


def test_backend_readiness_uses_healthz_while_liveness_stays_transport_level() -> None:
    """Readiness should respect outbox pressure; liveness only checks the socket."""
    container = backend_deployment()["spec"]["template"]["spec"]["containers"][0]
    readiness = container["readinessProbe"]
    assert readiness["httpGet"]["path"] == "/healthz"
    assert readiness["httpGet"]["port"] == 8000
    assert readiness["failureThreshold"] == 10

    liveness = container["livenessProbe"]
    assert liveness["tcpSocket"]["port"] == 8000


def test_backend_database_credentials_come_from_secrets() -> None:
    """DATABASE_URL and JWT_SECRET must never be inlined in the Deployment."""
    container = backend_deployment()["spec"]["template"]["spec"]["containers"][0]
    env = {entry["name"]: entry for entry in container["env"]}
    assert env["DATABASE_URL"]["valueFrom"]["secretKeyRef"]["name"] == "backend-secrets"
    assert env["JWT_SECRET"]["valueFrom"]["secretKeyRef"]["name"] == "backend-secrets"
