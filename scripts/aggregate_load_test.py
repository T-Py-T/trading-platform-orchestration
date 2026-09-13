#!/usr/bin/env python3
# hft-trading-app/scripts/aggregate_load_test.py
# Aggregate results from distributed load test

import json
import statistics
import sys


def main():
    """Aggregate load test results from multiple clients"""

    results = []
    total_orders = 0
    total_success = 0
    all_latencies = []

    print("Parsing results from stdin...")

    for line in sys.stdin:
        if line.startswith("JSON:"):
            try:
                data = json.loads(line[5:])
                results.append(data)
                total_orders += data["orders_sent"]
                total_success += data["orders_success"]
                all_latencies.append(data["avg_latency"])
            except json.JSONDecodeError:
                print(f"Failed to parse: {line}", file=sys.stderr)

    if not results:
        print("No results collected", file=sys.stderr)
        return

    # Aggregate results
    print("\n" + "=" * 80)
    print("DISTRIBUTED LOAD TEST RESULTS")
    print("=" * 80)

    print(f"\nClients: {len(results)}")
    print(f"Total orders: {total_orders}")
    print(f"Total successful: {total_success}")
    print(f"Success rate: {(total_success/total_orders)*100:.1f}%")

    if all_latencies:
        print("\nLatency statistics:")
        print(f"  Average: {statistics.mean(all_latencies):.2f}ms")
        print(f"  Median: {statistics.median(all_latencies):.2f}ms")
        if len(all_latencies) > 1:
            print(f"  Stdev: {statistics.stdev(all_latencies):.2f}ms")

    # Per-client breakdown
    print("\nPer-client breakdown:")
    total_throughput = 0
    for r in results:
        print(f"  Client {r['client_id']}: {r['throughput']:.0f} orders/sec")
        total_throughput += r["throughput"]

    print("\n" + "=" * 80)
    print(f"TOTAL THROUGHPUT: {total_throughput:.0f} orders/sec")
    print("=" * 80)

    # Validation
    if total_throughput >= 10000:
        print("STATUS: TARGET ACHIEVED (10,000+ orders/sec)")
    elif total_throughput >= 5000:
        print("STATUS: GREAT (5,000+ orders/sec)")
    elif total_throughput >= 1074:
        print(f"STATUS: Improvement ({total_throughput:.0f} vs 1,074)")
    else:
        print("STATUS: Below expected")


if __name__ == "__main__":
    main()
