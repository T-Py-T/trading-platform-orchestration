"""CLI-level tests for distributed load-test aggregation (stdin JSON lines)."""

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


def sample_client_payload(
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
        "max_latency": avg_latency * 2,
    }
    return f"JSON:{json.dumps(payload)}\n"


def test_aggregate_reports_combined_throughput() -> None:
    """Multiple client JSON lines should roll up into a single throughput total."""
    stdin = "".join(
        [
            sample_client_payload(0, orders_sent=100, orders_success=95, throughput=4000, avg_latency=2.0),
            sample_client_payload(1, orders_sent=120, orders_success=110, throughput=1500, avg_latency=2.5),
        ]
    )
    result = run_aggregate(stdin)

    assert result.returncode == 0, result.stderr
    assert "DISTRIBUTED LOAD TEST RESULTS" in result.stdout
    assert "Clients: 2" in result.stdout
    assert "Total orders: 220" in result.stdout
    assert "Total successful: 205" in result.stdout
    assert "TOTAL THROUGHPUT: 5500 orders/sec" in result.stdout
    assert "STATUS: GREAT (5,000+ orders/sec)" in result.stdout


def test_aggregate_skips_malformed_json_lines() -> None:
    """Invalid JSON: lines should not abort aggregation of valid client output."""
    stdin = (
        "JSON:{not valid}\n"
        + sample_client_payload(3, orders_sent=10, orders_success=10, throughput=12000, avg_latency=1.0)
    )
    result = run_aggregate(stdin)

    assert result.returncode == 0, result.stderr
    assert "Clients: 1" in result.stdout
    assert "STATUS: TARGET ACHIEVED (10,000+ orders/sec)" in result.stdout
    assert "Failed to parse" in result.stderr


def test_aggregate_with_no_input_exits_cleanly() -> None:
    """Empty stdin should not raise; operators rely on a non-zero-free no-op."""
    result = run_aggregate("")

    assert result.returncode == 0
    assert "No results collected" in result.stderr
