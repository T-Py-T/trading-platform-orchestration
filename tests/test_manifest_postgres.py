"""Offline contract tests for the single-node Postgres Kubernetes manifest."""

from test_gitroll_manifests import ROOT, load_documents, workloads


def postgres_statefulset() -> dict:
    return workloads("k8s/base/postgres.yaml")[0]


def postgres_config() -> dict:
    documents = load_documents("k8s/base/postgres.yaml")
    return next(document for document in documents if document["kind"] == "ConfigMap")


def postgres_service() -> dict:
    documents = load_documents("k8s/base/postgres.yaml")
    return next(document for document in documents if document["kind"] == "Service")


def test_postgres_service_is_headless_for_statefulset_dns() -> None:
    """StatefulSet pods need a headless Service for stable network identity."""
    service = postgres_service()
    assert service["spec"]["clusterIP"] == "None"
    assert service["spec"]["ports"][0]["port"] == 5432


def test_postgres_credentials_come_from_configmap_and_secret() -> None:
    """Database name and user are config; password must be injected at deploy time."""
    container = postgres_statefulset()["spec"]["template"]["spec"]["containers"][0]
    env_from = container["envFrom"]
    refs = {(item.get("configMapRef", {}).get("name"), item.get("secretRef", {}).get("name")) for item in env_from}
    assert ("postgres-config", None) in refs
    assert (None, "postgres-secret") in refs

    config = postgres_config()["data"]
    assert config["POSTGRES_DB"] == "trading_db"
    assert config["POSTGRES_USER"] == "trading_user"


def test_postgres_statefulset_wires_service_name_and_persistence() -> None:
    """The workload must bind to its Service and request durable storage."""
    statefulset = postgres_statefulset()
    assert statefulset["spec"]["serviceName"] == "postgres"

    volume_claim = statefulset["spec"]["volumeClaimTemplates"][0]
    assert volume_claim["spec"]["accessModes"] == ["ReadWriteOnce"]
    assert volume_claim["spec"]["resources"]["requests"]["storage"] == "10Gi"

    mount = statefulset["spec"]["template"]["spec"]["containers"][0]["volumeMounts"][0]
    assert mount["mountPath"] == "/var/lib/postgresql/data"


def test_postgres_image_matches_compose_pin() -> None:
    """Local compose and cluster Postgres should use the same digest-pinned image."""
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    container = postgres_statefulset()["spec"]["template"]["spec"]["containers"][0]
    image = container["image"]
    assert image.startswith("postgres:18.6-alpine@sha256:")
    assert image in compose
