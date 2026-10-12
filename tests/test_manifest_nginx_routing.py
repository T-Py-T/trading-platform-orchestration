"""Offline checks for nginx ingress proxy wiring in Kubernetes."""

from test_gitroll_manifests import load_documents, workloads


def nginx_config_text() -> str:
    documents = load_documents("k8s/base/nginx-ingress.yaml")
    config_map = next(document for document in documents if document["kind"] == "ConfigMap")
    return config_map["data"]["nginx.conf"]


def nginx_deployment() -> dict:
    return workloads("k8s/base/nginx-ingress.yaml")[0]


def test_nginx_config_routes_to_backend_service_pool() -> None:
    """External HTTP traffic must proxy to the Go API Service on port 8000."""
    config = nginx_config_text()
    assert "upstream backend_pool" in config
    assert "server hft-backend:8000" in config
    assert "proxy_pass http://backend_pool" in config
    assert "listen 8080" in config


def test_nginx_deployment_mounts_generated_config() -> None:
    """The controller pod must load nginx.conf from the nginx-config ConfigMap."""
    deployment = nginx_deployment()
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    mount = container["volumeMounts"][0]
    assert mount["subPath"] == "nginx.conf"
    assert mount["mountPath"] == "/etc/nginx/nginx.conf"

    volume = deployment["spec"]["template"]["spec"]["volumes"][0]
    assert volume["configMap"]["name"] == "nginx-config"


def test_nginx_load_balancer_exposes_http_on_port_80() -> None:
    """Clients should reach the ingress on standard HTTP while targeting listener 8080."""
    documents = load_documents("k8s/base/nginx-ingress.yaml")
    service = next(document for document in documents if document["kind"] == "Service")
    http_port = next(port for port in service["spec"]["ports"] if port["name"] == "http")
    assert service["spec"]["type"] == "LoadBalancer"
    assert http_port["port"] == 80
    assert http_port["targetPort"] == 8080
