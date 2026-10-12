"""Kubernetes namespace resource contract."""

from test_gitroll_manifests import load_documents


def test_namespace_manifest_names_hft_trading() -> None:
    """All base resources target the hft-trading namespace."""
    namespace = load_documents("k8s/base/namespace.yaml")[0]
    assert namespace["kind"] == "Namespace"
    assert namespace["metadata"]["name"] == "hft-trading"
    assert namespace["metadata"]["labels"]["name"] == "hft-trading"
