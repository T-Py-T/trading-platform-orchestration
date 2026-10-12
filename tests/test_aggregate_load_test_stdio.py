"""Subprocess tests for scripts/aggregate_load_test.py (stdin JSON lines)."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGGREGATE = ROOT / "scripts" / "aggregate_load_test.py"


def run_aggregate(stdin: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(AGGREGATE)],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def client_line(
    client_id: int,
    *,
    orders_sent: int,
    orders_success: int,
    throughput: float,
    avg_latency: float,
) -> str:
    payload = {
        "client_id": client_id,
        "orders_sent": orders_sent,
        "orders_success": orders_success,
        "throughput": throughput,
        "avg_latency": avg_latency,
    }
    return f"JSON:{json.dumps(payload)}\n"


def test_aggregate_reports_great_status_for_high_throughput() -> None:
    stdin = client_line(1, orders_sent=50, orders_success=50, throughput=6000.0, avg_latency=2.0)
    result = run_aggregate(stdin)
    assert result.returncode == 0
    assert "DISTRIBUTED LOAD TEST RESULTS" in result.stdout
    assert "STATUS: GREAT (5,000+ orders/sec)" in result.stdout
    assert "Success rate: 100.0%" in result.stdout


def test_aggregate_sums_throughput_across_clients() -> None:
    stdin = "".join(
        [
            client_line(0, orders_sent=10, orders_success=10, throughput=1000.0, avg_latency=1.0),
            client_line(1, orders_sent=10, orders_success=10, throughput=2500.0, avg_latency=1.5),
        ]
    )
    result = run_aggregate(stdin)
    assert result.returncode == 0
    assert "TOTAL THROUGHPUT: 3500 orders/sec" in result.stdout


def test_aggregate_skips_malformed_json_lines() -> None:
    stdin = "JSON:{not-json}\n" + client_line(
        3, orders_sent=5, orders_success=5, throughput=120.0, avg_latency=4.0
    )
    result = run_aggregate(stdin)
    assert result.returncode == 0
    assert "Failed to parse" in result.stderr
    assert "Clients: 1" in result.stdout


def test_aggregate_writes_no_results_message_when_input_empty() -> None:
    result = run_aggregate("")
    assert result.returncode == 0
    assert "No results collected" in result.stderr
