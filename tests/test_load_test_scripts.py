"""Unit tests for distributed load test tooling in scripts/."""

import asyncio
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_script_module(filename: str, module_name: str) -> ModuleType:
    """Import a script from scripts/ as a testable module."""
    path = SCRIPTS / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


aggregate = load_script_module("aggregate_load_test.py", "aggregate_load_test")
distributed = load_script_module("distributed_load_test.py", "distributed_load_test")


class TestAggregateLoadTest:
    def test_parse_client_result_line_accepts_json_prefix(self) -> None:
        payload = {
            "client_id": 1,
            "orders_sent": 10,
            "orders_success": 9,
            "throughput": 120.5,
            "avg_latency": 3.2,
        }
        line = f"JSON:{json.dumps(payload)}\n"
        assert aggregate.parse_client_result_line(line) == payload

    def test_parse_client_result_line_ignores_non_json(self) -> None:
        assert aggregate.parse_client_result_line("not json\n") is None

    def test_parse_client_result_line_rejects_malformed_json(self) -> None:
        assert aggregate.parse_client_result_line("JSON:{not valid}\n") is None

    def test_aggregate_client_results_handles_zero_orders(self) -> None:
        results = [
            {
                "client_id": 0,
                "orders_sent": 0,
                "orders_success": 0,
                "throughput": 0.0,
                "avg_latency": 0.0,
            }
        ]
        summary = aggregate.aggregate_client_results(results)
        assert summary["success_rate_pct"] == 0.0
        assert summary["total_orders"] == 0

    def test_throughput_status_thresholds(self) -> None:
        assert "TARGET ACHIEVED" in aggregate.throughput_status(10000)
        assert "GREAT" in aggregate.throughput_status(5000)
        assert "Improvement" in aggregate.throughput_status(2000)
        assert aggregate.throughput_status(100) == "STATUS: Below expected"

    def test_main_exits_nonzero_when_no_results(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "aggregate_load_test.py")],
            input="",
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 1
        assert "No results collected" in result.stderr

    def test_main_prints_report_for_valid_input(self) -> None:
        payload = {
            "client_id": 2,
            "orders_sent": 100,
            "orders_success": 95,
            "throughput": 6000.0,
            "avg_latency": 1.5,
        }
        stdin = f"noise\nJSON:{json.dumps(payload)}\n"
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "aggregate_load_test.py")],
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "DISTRIBUTED LOAD TEST RESULTS" in result.stdout
        assert "STATUS: GREAT" in result.stdout


@pytest.mark.asyncio
async def test_load_test_client_stops_when_registration_fails() -> None:
    client = distributed.LoadTestClient(7, "http://example.test", duration_sec=1)

    mock_response = MagicMock()
    mock_response.status_code = 400

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_response)
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=None)

    with patch.object(distributed.httpx, "AsyncClient", return_value=mock_http):
        await client.run()

    assert client.orders_sent == 0
    mock_http.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_load_test_client_counts_successful_orders() -> None:
    client = distributed.LoadTestClient(3, "http://example.test", duration_sec=1)

    register_response = MagicMock()
    register_response.status_code = 201
    register_response.json.return_value = {"access_token": "token"}

    order_ok = MagicMock()
    order_ok.status_code = 201

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(side_effect=[register_response, order_ok, order_ok])
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=None)

    perf_times = [0.0, 0.0, 0.01, 0.02, 0.5, 0.51, 0.52, 2.0, 2.0]
    with (
        patch.object(distributed.httpx, "AsyncClient", return_value=mock_http),
        patch.object(distributed.time, "perf_counter", side_effect=perf_times),
    ):
        await client.run()

    assert client.orders_sent == 2
    assert client.orders_success == 2
    assert client.latencies


def test_setup_test_db_requires_postgres_password() -> None:
    env = {"PATH": "/usr/bin:/bin"}
    result = subprocess.run(
        ["bash", str(SCRIPTS / "setup_test_db.sh")],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "POSTGRES_PASSWORD" in result.stderr
