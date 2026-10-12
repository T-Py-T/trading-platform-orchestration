"""Contract tests for Go backend outbox / write-behind ConfigMap settings."""

from test_gitroll_manifests import load_documents


def backend_config_data() -> dict[str, str]:
    documents = load_documents("k8s/base/hft-backend.yaml")
    config_map = next(document for document in documents if document["kind"] == "ConfigMap")
    assert config_map["metadata"]["name"] == "backend-config"
    return config_map["data"]


def test_write_behind_outbox_tuning_matches_go_backend_defaults() -> None:
    """Outbox buffer and flush settings must stay aligned with the Go server implementation."""
    data = backend_config_data()
    assert data["WRITE_BEHIND"] == "true"
    assert data["OUTBOX_BUFFER"] == "10000"
    assert data["OUTBOX_BATCH"] == "50"
    assert data["OUTBOX_FLUSH"] == "50ms"
    assert data["OUTBOX_LAG_THRESHOLD"] == "5s"


def test_backend_listens_on_cluster_http_port() -> None:
    """HTTP_ADDR must match Service and probe ports."""
    data = backend_config_data()
    assert data["HTTP_ADDR"] == ":8000"
    assert data["LOG_FORMAT"] == "json"
