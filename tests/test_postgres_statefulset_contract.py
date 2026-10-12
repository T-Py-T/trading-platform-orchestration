"""PostgreSQL StatefulSet storage and discovery contract."""

from test_gitroll_manifests import load_documents, workloads


def postgres_documents() -> list[dict]:
    return load_documents("k8s/base/postgres.yaml")


def test_postgres_service_is_headless_for_stable_dns() -> None:
    """StatefulSet pods need per-pod DNS records via clusterIP: None."""
    service = next(doc for doc in postgres_documents() if doc["kind"] == "Service")
    assert service["spec"]["clusterIP"] == "None"
    assert service["spec"]["ports"][0]["port"] == 5432
    assert service["spec"]["selector"]["app"] == "postgres"


def test_postgres_statefulset_wires_config_and_runtime_secrets() -> None:
    """Credentials must come from a Secret; only non-secret fields sit in the ConfigMap."""
    statefulset = workloads("k8s/base/postgres.yaml")[0]
    container = statefulset["spec"]["template"]["spec"]["containers"][0]
    env_from = container["envFrom"]
    assert {"configMapRef": {"name": "postgres-config"}} in env_from
    assert {"secretRef": {"name": "postgres-secret"}} in env_from

    config_map = next(doc for doc in postgres_documents() if doc["kind"] == "ConfigMap")
    assert config_map["data"]["POSTGRES_DB"] == "trading_db"
    assert config_map["data"]["POSTGRES_USER"] == "trading_user"
    assert "POSTGRES_PASSWORD" not in config_map["data"]


def test_postgres_statefulset_requests_persistent_volume_per_pod() -> None:
    """Each replica should claim dedicated ReadWriteOnce storage."""
    statefulset = workloads("k8s/base/postgres.yaml")[0]
    assert statefulset["spec"]["serviceName"] == "postgres"
    pvc = statefulset["spec"]["volumeClaimTemplates"][0]
    assert pvc["metadata"]["name"] == "postgres-data"
    assert pvc["spec"]["accessModes"] == ["ReadWriteOnce"]
    assert pvc["spec"]["resources"]["requests"]["storage"] == "10Gi"

    probe = statefulset["spec"]["template"]["spec"]["containers"][0]["livenessProbe"]
    assert probe["exec"]["command"] == ["pg_isready", "-U", "trading_user"]
