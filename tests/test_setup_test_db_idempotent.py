"""Regression: setup_test_db.sh must tolerate an existing test database."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_setup_test_db_is_idempotent(tmp_path: Path) -> None:
    """Repeated setup must not re-issue CREATE DATABASE for trading_db_test."""
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    log = tmp_path / "psql.log"
    db_flag = tmp_path / "trading_db_test.exists"
    psql = mock_bin / "psql"
    psql.write_text(
        f"""#!/bin/bash
set -eu
printf '%s\\n' "$*" >> "{log}"
body=$(cat)
printf '%s\\n' "$body" >> "{log}"
if grep -q 'NOT EXISTS' <<<"$body"; then
  if [[ -f "{db_flag}" ]]; then
    exit 0
  fi
  touch "{db_flag}"
  echo "EXECUTED: CREATE DATABASE trading_db_test" >> "{log}"
  exit 0
fi
if grep -q 'CREATE DATABASE trading_db_test' <<<"$body"; then
  if [[ -f "{db_flag}" ]]; then
    echo "duplicate create" >> "{log}"
    exit 1
  fi
  touch "{db_flag}"
fi
exit 0
""",
        encoding="utf-8",
    )
    psql.chmod(0o755)
    pg_isready = mock_bin / "pg_isready"
    pg_isready.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    pg_isready.chmod(0o755)

    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{mock_bin}{os.pathsep}{environment['PATH']}",
            "POSTGRES_PASSWORD": "test-password",
        }
    )

    script = ROOT / "scripts/setup_test_db.sh"
    for _ in range(2):
        result = subprocess.run(
            ["bash", str(script)],
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr + result.stdout

    log_text = log.read_text(encoding="utf-8")
    assert log_text.count("EXECUTED: CREATE DATABASE trading_db_test") == 1
    assert "duplicate create" not in log_text
