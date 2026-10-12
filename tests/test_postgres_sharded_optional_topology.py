"""Optional three-shard Postgres manifest is present but not part of the default bundle."""

import yaml

from test_gitroll_manifests import ROOT, load_documents, workloads


def base_kustomization_resources() -> list[str]:
    with (ROOT / "k8s/base/kustomization.yaml").open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)["resources"]


def test_sharded_postgres_not_in_default_kustomization() -> None:
    assert "postgres-sharded.yaml" not in base_kustomization_resources()


def test_sharded_manifest_declares_three_stateful_shards() -> None:
    names = {
        workload["metadata"]["name"] for workload in workloads("k8s/base/postgres-sharded.yaml")
    }
    assert names == {"postgres-shard-0", "postgres-shard-1", "postgres-shard-2"}


def test_each_shard_requests_dedicated_persistent_volume() -> None:
    for shard_id in range(3):
        statefulset = next(
            workload
            for workload in workloads("k8s/base/postgres-sharded.yaml")
            if workload["metadata"]["name"] == f"postgres-shard-{shard_id}"
        )
        claim = statefulset["spec"]["volumeClaimTemplates"][0]
        assert claim["metadata"]["name"] == "postgres-data"
        assert claim["spec"]["accessModes"] == ["ReadWriteOnce"]
