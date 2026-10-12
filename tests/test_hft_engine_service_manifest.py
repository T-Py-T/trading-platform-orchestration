"""HFT engine Service and Deployment port contract."""

from test_gitroll_manifests import load_documents, workloads


def engine_service() -> dict:
    documents = load_documents("k8s/base/hft-engine.yaml")
    return next(document for document in documents if document["kind"] == "Service")


def engine_deployment() -> dict:
    return workloads("k8s/base/hft-engine.yaml")[0]


def test_engine_service_exposes_grpc_and_udp_ports() -> None:
    """Clients must reach gRPC on 50051 and the UDP feed on 9001."""
    service = engine_service()
    ports = {port["name"]: port for port in service["spec"]["ports"]}
    assert ports["grpc"]["port"] == 50051
    assert ports["grpc"]["targetPort"] == 50051
    assert ports["udp"]["port"] == 9001
    assert ports["udp"]["protocol"] == "UDP"


def test_engine_container_ports_match_service_endpoints() -> None:
    """Pod ports should line up with the ClusterIP service definition."""
    deployment = engine_deployment()
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    named_ports = {port["name"]: port for port in container["ports"]}
    assert named_ports["grpc"]["containerPort"] == 50051
    assert named_ports["udp"]["containerPort"] == 9001
    assert named_ports["udp"]["protocol"] == "UDP"


def test_engine_liveness_checks_grpc_listener_not_http() -> None:
    """The C++ engine speaks gRPC; liveness should probe the TCP listener."""
    deployment = engine_deployment()
    probe = deployment["spec"]["template"]["spec"]["containers"][0]["livenessProbe"]
    assert probe["tcpSocket"]["port"] == 50051
    assert probe["initialDelaySeconds"] == 10
