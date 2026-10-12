"""Static contract checks for scripts/init_db.py (no database required)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT_DB = ROOT / "scripts" / "init_db.py"


def test_init_db_is_async_entrypoint_without_hardcoded_secrets() -> None:
    """Schema bootstrap should use application settings, not embedded credentials."""
    source = INIT_DB.read_text(encoding="utf-8")
    assert "asyncio.run(init_db())" in source
    assert "create_async_engine" in source
    assert "Base.metadata.create_all" in source
    lowered = source.lower()
    assert "password" not in lowered or "database_async_url" in source
    assert "trading_password" not in source


def test_init_db_documents_ml_trading_app_py_path() -> None:
    """The helper expects the legacy Python backend tree for SQLAlchemy models."""
    source = INIT_DB.read_text(encoding="utf-8")
    assert "ml-trading-app-py" in source
