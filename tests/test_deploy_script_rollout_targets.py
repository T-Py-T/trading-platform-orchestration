"""Deploy script should track workloads that actually ship in the base bundle."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY_SCRIPT = ROOT / "k8s/deploy.sh"


def test_deploy_waits_for_go_api_engine_and_ingress() -> None:
    """Rollout status should cover the services defined in the base kustomization."""
    text = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    rollout_line = text.split("DEPLOYMENTS=(")[1].split(")")[0]
    for deployment in ("hft-backend", "hft-engine", "nginx-ingress"):
        assert deployment in rollout_line


def test_deploy_requires_runtime_secrets_before_cluster_apply() -> None:
    """DATABASE_URL, JWT_SECRET, and POSTGRES_PASSWORD must be present to deploy."""
    text = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    for secret_var in ("POSTGRES_PASSWORD", "DATABASE_URL", "JWT_SECRET"):
        assert secret_var in text
    assert 'for secret_var in POSTGRES_PASSWORD DATABASE_URL JWT_SECRET' in text


def test_deploy_statefulset_list_includes_postgres_only() -> None:
    """The default stack persists orders in a single Postgres StatefulSet."""
    text = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    assert 'STATEFULSETS=("postgres")' in text
