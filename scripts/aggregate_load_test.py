#!/usr/bin/env python3
# hft-trading-app/scripts/aggregate_load_test.py
# Aggregate results from distributed load test

import json
import statistics
import sys
from typing import Any


def parse_client_result_line(line: str) -> dict[str, Any] | None:
    """Parse a single ``JSON:`` line emitted by distributed_load_test clients."""
    if not line.startswith("JSON:"):
        return None
    try:
        return json.loads(line[5:])
    except json.JSONDecodeError:
        print(f"Failed to parse: {line}", file=sys.stderr)
        return None


def aggregate_client_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize per-client load test payloads."""
    total_orders = sum(data["orders_sent"] for data in results)
    total_success = sum(data["orders_success"] for data in results)
    all_latencies = [data["avg_latency"] for data in results]
    total_throughput = sum(data["throughput"] for data in results)
    success_rate_pct = (total_success / total_orders) * 100 if total_orders else 0.0
    return {
        "client_count": len(results),
        "total_orders": total_orders,
        "total_success": total_success,
        "success_rate_pct": success_rate_pct,
        "all_latencies": all_latencies,
        "total_throughput": total_throughput,
        "results": results,
    }


def throughput_status(total_throughput: float) -> str:
    """Map aggregate throughput to the script's status message."""
    if total_throughput >= 10000:
        return "STATUS: TARGET ACHIEVED (10,000+ orders/sec)"
    if total_throughput >= 5000:
        return "STATUS: GREAT (5,000+ orders/sec)"
    if total_throughput >= 1074:
        return f"STATUS: Improvement ({total_throughput:.0f} vs 1,074)"
    return "STATUS: Below expected"


def print_report(summary: dict[str, Any]) -> None:
    """Print the human-readable aggregation report."""
    results = summary["results"]
    all_latencies = summary["all_latencies"]
    total_throughput = summary["total_throughput"]

    print("\n" + "=" * 80)
    print("DISTRIBUTED LOAD TEST RESULTS")
    print("=" * 80)

    print(f"\nClients: {summary['client_count']}")
    print(f"Total orders: {summary['total_orders']}")
    print(f"Total successful: {summary['total_success']}")
    print(f"Success rate: {summary['success_rate_pct']:.1f}%")

    if all_latencies:
        print("\nLatency statistics:")
        print(f"  Average: {statistics.mean(all_latencies):.2f}ms")
        print(f"  Median: {statistics.median(all_latencies):.2f}ms")
        if len(all_latencies) > 1:
            print(f"  Stdev: {statistics.stdev(all_latencies):.2f}ms")

    print("\nPer-client breakdown:")
    for result in results:
        print(f"  Client {result['client_id']}: {result['throughput']:.0f} orders/sec")

    print("\n" + "=" * 80)
    print(f"TOTAL THROUGHPUT: {total_throughput:.0f} orders/sec")
    print("=" * 80)
    print(throughput_status(total_throughput))


def main() -> int:
    """Aggregate load test results from multiple clients."""
    results: list[dict[str, Any]] = []

    print("Parsing results from stdin...")

    for line in sys.stdin:
        parsed = parse_client_result_line(line)
        if parsed is not None:
            results.append(parsed)

    if not results:
        print("No results collected", file=sys.stderr)
        return 1

    print_report(aggregate_client_results(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
