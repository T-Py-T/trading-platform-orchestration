"""Contract tests for the optional three-shard Postgres reference manifest."""

import pytest

from test_gitroll_manifests import load_documents, workloads

SHARD_IDS = (0, 1, 2)


def shard_config(shard_id: int) -> dict:
    documents = load_documents("k8s/base/postgres-sharded.yaml")
    name = f"postgres-shard-{shard_id}-config"
    return next(document for document in documents if document.get("metadata", {}).get("name") == name)


def shard_statefulset(shard_id: int) -> dict:
    name = f"postgres-shard-{shard_id}"
    return next(
        workload
        for workload in workloads("k8s/base/postgres-sharded.yaml")
        if workload["metadata"]["name"] == name
    )


def test_sharded_manifest_defines_three_independent_statefulsets() -> None:
    """Horizontal scaling design expects three isolated shard StatefulSets."""
    names = {workload["metadata"]["name"] for workload in workloads("k8s/base/postgres-sharded.yaml")}
    assert names == {f"postgres-shard-{shard_id}" for shard_id in SHARD_IDS}


@pytest.mark.parametrize("shard_id", SHARD_IDS)
def test_each_shard_has_matching_service_and_secret_reference(shard_id: int) -> None:
    """Every shard must expose a headless Service and mount its own secret."""
    statefulset = shard_statefulset(shard_id)
    assert statefulset["spec"]["serviceName"] == f"postgres-shard-{shard_id}"

    container = statefulset["spec"]["template"]["spec"]["containers"][0]
    secret_refs = [
        item["secretRef"]["name"]
        for item in container["envFrom"]
        if "secretRef" in item
    ]
    assert secret_refs == [f"postgres-shard-{shard_id}-secret"]

    config = shard_config(shard_id)["data"]
    assert config["SHARD_ID"] == str(shard_id)
    assert config["POSTGRES_DB"] == "trading_db"
