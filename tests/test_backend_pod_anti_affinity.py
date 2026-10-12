"""Scheduling policy checks for the Go API Deployment."""

from test_gitroll_manifests import workloads


def backend_pod_spec() -> dict:
    deployment = workloads("k8s/base/hft-backend.yaml")[0]
    return deployment["spec"]["template"]["spec"]


def test_backend_prefers_spreading_across_nodes() -> None:
    """HA rollouts should prefer distinct nodes for concurrent backend pods."""
    affinity = backend_pod_spec()["affinity"]["podAntiAffinity"]
    rules = affinity["preferredDuringSchedulingIgnoredDuringExecution"]
    assert len(rules) >= 1

    term = rules[0]["podAffinityTerm"]
    assert term["topologyKey"] == "kubernetes.io/hostname"
    match = term["labelSelector"]["matchExpressions"][0]
    assert match["key"] == "app"
    assert match["operator"] == "In"
    assert "hft-backend" in match["values"]


def test_backend_rolling_update_avoids_capacity_dip() -> None:
    """Surge without unavailability keeps the API reachable during deploys."""
    deployment = workloads("k8s/base/hft-backend.yaml")[0]
    rolling = deployment["spec"]["strategy"]["rollingUpdate"]
    assert deployment["spec"]["strategy"]["type"] == "RollingUpdate"
    assert rolling["maxUnavailable"] == 0
    assert rolling["maxSurge"] == 1
