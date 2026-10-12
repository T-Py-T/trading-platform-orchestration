"""Regression tests for concrete bugs not covered by open draft PRs #28–#36."""

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from test_gitroll_manifests import load_documents

ROOT = Path(__file__).resolve().parents[1]
DISTRIBUTED_SCRIPT = ROOT / "scripts" / "distributed_load_test.py"


def load_distributed_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "distributed_load_test_regression", DISTRIBUTED_SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def nginx_health_location_block() -> str:
    config = load_documents("k8s/base/nginx-ingress.yaml")
    config_map = next(doc for doc in config if doc["kind"] == "ConfigMap")
    text = config_map["data"]["nginx.conf"]
    match = re.search(r"location /health \{[^}]+\}", text, re.MULTILINE)
    assert match is not None, "nginx.conf must define a /health location"
    return match.group(0)


def test_nginx_health_sets_content_type_before_return() -> None:
    """add_header after return is ignored; Content-Type must be set first."""
    block = nginx_health_location_block()
    content_type_idx = block.index("add_header Content-Type")
    return_idx = block.index("return 200")
    assert content_type_idx < return_idx


@pytest.mark.asyncio
async def test_distributed_load_test_counts_http_error_status_as_errors() -> None:
    """Non-2xx order responses should increment errors, not only transport failures."""
    distributed = load_distributed_module()
    client = distributed.LoadTestClient(1, "http://api.test", duration_sec=1)

    register_response = MagicMock()
    register_response.status_code = 201
    register_response.json.return_value = {"access_token": "token"}

    order_response = MagicMock()
    order_response.status_code = 503

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(side_effect=[register_response, order_response])
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=None)

    with (
        patch.object(distributed.httpx, "AsyncClient", return_value=mock_http),
        patch.object(
            distributed.time,
            "perf_counter",
            side_effect=[0.0, 0.0, 0.0, 0.1, 1.0, 1.0],
        ),
    ):
        await client.run()

    assert client.orders_sent == 1
    assert client.orders_success == 0
    assert client.errors == 1
