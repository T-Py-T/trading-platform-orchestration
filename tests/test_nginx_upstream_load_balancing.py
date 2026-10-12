"""Nginx ingress proxy tuning checks (offline ConfigMap text)."""

from test_gitroll_manifests import load_documents


def nginx_conf() -> str:
    documents = load_documents("k8s/base/nginx-ingress.yaml")
    config_map = next(document for document in documents if document["kind"] == "ConfigMap")
    return config_map["data"]["nginx.conf"]


def test_upstream_uses_least_conn_with_keepalive_pool() -> None:
    """API load should spread across backends with connection reuse to the Go server."""
    conf = nginx_conf()
    assert "upstream backend_pool" in conf
    assert "least_conn;" in conf
    assert "keepalive 32;" in conf


def test_nginx_health_stub_and_body_size_limits() -> None:
    """Edge health must be cheap; uploads are capped for API safety."""
    conf = nginx_conf()
    assert "location /health" in conf
    assert 'return 200 "OK\\n"' in conf or 'return 200 "OK\n"' in conf
    assert "client_max_body_size 20M" in conf
    assert "access_log off" in conf.split("location /health")[1].split("location /")[0]
