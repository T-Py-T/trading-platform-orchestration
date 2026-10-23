#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  PYTHON=python3
fi

"$PYTHON" -m pip install --disable-pip-version-check pre-commit==4.6.2
"$PYTHON" -m pre_commit run --all-files --show-diff-on-failure --config .pre-commit/.pre-commit-config.yaml

"$PYTHON" -m pip install --disable-pip-version-check -r requirements.txt
"$PYTHON" -m pytest tests/test_gitroll_manifests.py -v --tb=short
