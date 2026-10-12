"""Unit tests for scripts/distributed_load_test.py with mocked HTTP."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "distributed_load_test.py"


def load_distributed_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("distributed_load_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


distributed = load_distributed_module()


@pytest.mark.asyncio
async def test_load_test_client_emits_json_summary_after_successful_order() -> None:
    """Aggregation tooling expects a JSON: line with per-client throughput stats."""
    client = distributed.LoadTestClient(4, "http://api.test", duration_sec=1)

    register_response = MagicMock()
    register_response.status_code = 201
    register_response.json.return_value = {"access_token": "token-abc"}

    order_response = MagicMock()
    order_response.status_code = 201

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(side_effect=[register_response, order_response])
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=None)

    printed: list[str] = []

    def capture_print(*args: object, **kwargs: object) -> None:
        printed.append(" ".join(str(arg) for arg in args))

    with (
        patch.object(distributed.httpx, "AsyncClient", return_value=mock_http),
        patch.object(
            distributed.time,
            "perf_counter",
            side_effect=[0.0, 0.0, 0.0, 0.25, 1.0, 1.0],
        ),
        patch("builtins.print", side_effect=capture_print),
    ):
        await client.run()

    assert client.orders_sent == 1
    assert client.orders_success == 1
    json_lines = [line for line in printed if line.startswith("JSON:")]
    assert len(json_lines) == 1
    payload = json.loads(json_lines[0][5:])
    assert payload["client_id"] == 4
    assert payload["orders_sent"] == 1
    assert payload["orders_success"] == 1
    assert payload["throughput"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_load_test_client_alternates_order_side() -> None:
    """Market-making style load uses BUY/SELL alternation by order count."""
    client = distributed.LoadTestClient(1, "http://api.test", duration_sec=1)

    register_response = MagicMock()
    register_response.status_code = 201
    register_response.json.return_value = {"access_token": "token"}

    order_response = MagicMock()
    order_response.status_code = 200

    mock_http = AsyncMock()

    async def post(url: str, *args: object, **kwargs: object) -> MagicMock:
        if url.endswith("/api/auth/register"):
            return register_response
        body = kwargs.get("json", {})
        side = body.get("side")
        if client.orders_sent == 0:
            assert side == "BUY"
        else:
            assert side == "SELL"
        return order_response

    mock_http.post = AsyncMock(side_effect=post)
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=None)

    with (
        patch.object(distributed.httpx, "AsyncClient", return_value=mock_http),
        patch.object(
            distributed.time,
            "perf_counter",
            side_effect=[
                0.0,  # start
                0.0,  # while enter (order 1)
                0.0,  # req_start order 1
                0.01,  # latency end order 1
                0.02,  # while enter (order 2)
                0.02,  # req_start order 2
                0.03,  # latency end order 2
                1.0,  # while exit
                1.0,  # elapsed
            ],
        ),
    ):
        await client.run()

    assert client.orders_sent == 2
    assert mock_http.post.await_count == 3
