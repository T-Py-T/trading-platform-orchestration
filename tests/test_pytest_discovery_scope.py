"""Guardrails for which integration assets pytest collects by default."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_integration_script_is_not_named_for_pytest_collection() -> None:
    """integration_test.py is a manual compose runner, not part of CI discovery."""
    integration = ROOT / "tests" / "integration_test.py"
    assert integration.is_file()
    assert not integration.name.startswith("test_")


def test_active_tests_live_under_tests_and_match_test_prefix() -> None:
    """pytest.ini limits discovery to test_*.py under the tests package."""
    test_files = sorted(path.name for path in (ROOT / "tests").glob("test_*.py"))
    assert "test_gitroll_manifests.py" in test_files
    assert "integration_test.py" not in test_files


def test_conftest_fixtures_are_available_to_test_modules() -> None:
    """Shared httpx/grpc fixtures remain importable for future service-backed tests."""
    from tests.conftest import API_TARGET, GRPC_TARGET

    assert API_TARGET.startswith("http://")
    assert GRPC_TARGET.endswith(":50051")
