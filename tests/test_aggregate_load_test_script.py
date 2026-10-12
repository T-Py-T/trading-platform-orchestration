"""Offline checks for scripts/aggregate_load_test.py aggregation logic."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGGREGATE_SCRIPT = ROOT / "scripts" / "aggregate_load_test.py"


def run_aggregate(stdin: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(AGGREGATE_SCRIPT)],
        input=stdin,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_aggregate_combines_client_json_lines_and_reports_throughput() -> None:
    """Multiple JSON: lines from distributed clients roll up into a single summary."""
    stdin = "\n".join(
        [
            "noise should be ignored",
            'JSON:{"client_id": 1, "orders_sent": 100, "orders_success": 99, '
            '"avg_latency": 1.5, "throughput": 6000}',
            'JSON:{"client_id": 2, "orders_sent": 100, "orders_success": 100, '
            '"avg_latency": 2.0, "throughput": 5500}',
        ]
    )
    result = run_aggregate(stdin + "\n")

    assert result.returncode == 0, result.stderr
    assert "Clients: 2" in result.stdout
    assert "Total orders: 200" in result.stdout
    assert "Total successful: 199" in result.stdout
    assert "Success rate: 99.5%" in result.stdout
    assert "TOTAL THROUGHPUT: 11500 orders/sec" in result.stdout
    assert "STATUS: TARGET ACHIEVED (10,000+ orders/sec)" in result.stdout


def test_aggregate_marks_target_achieved_at_ten_thousand_orders_per_sec() -> None:
    """The status banner should celebrate cluster-scale throughput."""
    stdin = (
        'JSON:{"client_id": 0, "orders_sent": 1, "orders_success": 1, '
        '"avg_latency": 0.1, "throughput": 10000}\n'
    )
    result = run_aggregate(stdin)

    assert result.returncode == 0, result.stderr
    assert "STATUS: TARGET ACHIEVED (10,000+ orders/sec)" in result.stdout


def test_aggregate_prints_error_when_no_json_lines() -> None:
    """Empty input should not pretend a load test ran."""
    result = run_aggregate("only plain logs\n")

    assert result.returncode == 0
    assert "No results collected" in result.stderr
