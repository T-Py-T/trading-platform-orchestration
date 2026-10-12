"""Unit tests for PerformanceMetrics in tests/integration_test.py (no live API)."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "tests" / "integration_test.py"


def load_integration_module():
    spec = importlib.util.spec_from_file_location("integration_test_module", INTEGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


integration = load_integration_module()
PerformanceMetrics = integration.PerformanceMetrics


def test_empty_summary_when_no_samples_recorded() -> None:
    metrics = PerformanceMetrics()
    assert metrics.get_summary() == {}


def test_summary_counts_success_and_failure_rates() -> None:
    metrics = PerformanceMetrics()
    metrics.start()
    metrics.record(12.5)
    metrics.record(20.0)
    metrics.record_failure()
    metrics.stop()

    summary = metrics.get_summary()
    # record_failure() does not increment total_requests; only latency samples do.
    assert summary["total_requests"] == 2
    assert summary["failed_requests"] == 1
    assert summary["successful_requests"] == 1
    assert summary["success_rate"] == "50.00%"
    assert summary["avg_response_time_ms"] == "16.25"
    assert summary["min_response_time_ms"] == "12.50"
    assert summary["max_response_time_ms"] == "20.00"
    assert float(summary["requests_per_second"]) > 0


def test_percentiles_use_sorted_latencies() -> None:
    metrics = PerformanceMetrics()
    for latency in (10.0, 30.0, 20.0, 40.0, 50.0):
        metrics.record(latency)
    metrics.start()
    metrics.stop()

    summary = metrics.get_summary()
    assert summary["median_response_time_ms"] == "30.00"
    assert summary["p95_response_time_ms"] == "50.00"
