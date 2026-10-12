"""Nginx ingress workload packaging (image pin and config volume wiring)."""

from test_gitroll_manifests import load_documents, workloads


def nginx_service() -> dict:
    documents = load_documents("k8s/base/nginx-ingress.yaml")
    return next(document for document in documents if document["kind"] == "Service")


def nginx_deployment() -> dict:
    return workloads("k8s/base/nginx-ingress.yaml")[0]


def test_nginx_service_publishes_load_balancer_http_and_api_ports() -> None:
    """External traffic enters on :80 while in-cluster callers can use :8080."""
    service = nginx_service()
    assert service["spec"]["type"] == "LoadBalancer"
    port_names = {port["name"]: port for port in service["spec"]["ports"]}
    assert port_names["http"]["port"] == 80
    assert port_names["api"]["port"] == 8080


def test_nginx_deployment_mounts_generated_config_as_single_file() -> None:
    """The controller should read nginx.conf from the hft-trading ConfigMap."""
    deployment = nginx_deployment()
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    mount = container["volumeMounts"][0]
    assert mount["name"] == "nginx-config-volume"
    assert mount["mountPath"] == "/etc/nginx/nginx.conf"
    assert mount["subPath"] == "nginx.conf"
    assert mount["readOnly"] is True

    volume = deployment["spec"]["template"]["spec"]["volumes"][0]
    assert volume["configMap"]["name"] == "nginx-config"


def test_nginx_image_is_digest_pinned() -> None:
    """Edge proxy should not float on an unpinned :latest tag."""
    deployment = nginx_deployment()
    image = deployment["spec"]["template"]["spec"]["containers"][0]["image"]
    assert image.startswith("nginx:1.31.5-alpine@sha256:")
