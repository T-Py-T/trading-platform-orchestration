#!/usr/bin/env python3
# tests/integration_test.py
# Integration tests for HFT Trading Platform
# Tests real-time order flow, position tracking, and performance metrics

import asyncio
import statistics
import sys
import time
from datetime import UTC, datetime

import httpx

BASE_URL = "http://localhost:8000"
# For testing, use a test token (backend should have test user endpoint)
HEADERS = {
    "Authorization": "Bearer test-token"  # Will be replaced with real auth in production
}
CLIENT = httpx.AsyncClient(base_url=BASE_URL, timeout=10.0, headers=HEADERS)


class PerformanceMetrics:
    """Track performance metrics for integration tests."""

    def __init__(self):
        self.response_times = []
        self.start_time = None
        self.end_time = None
        self.total_requests = 0
        self.failed_requests = 0

    def record(self, response_time: float):
        """Record a response time."""
        self.response_times.append(response_time)
        self.total_requests += 1

    def record_failure(self):
        """Record a failed request."""
        self.failed_requests += 1

    def start(self):
        """Start timing."""
        self.start_time = time.time()

    def stop(self):
        """Stop timing."""
        self.end_time = time.time()

    def get_summary(self) -> dict:
        """Get performance summary."""
        if not self.response_times:
            return {}

        return {
            "total_requests": self.total_requests,
            "successful_requests": self.total_requests - self.failed_requests,
            "failed_requests": self.failed_requests,
            "success_rate": f"{((self.total_requests - self.failed_requests) / self.total_requests * 100):.2f}%",
            "avg_response_time_ms": f"{statistics.mean(self.response_times):.2f}",
            "median_response_time_ms": f"{statistics.median(self.response_times):.2f}",
            "min_response_time_ms": f"{min(self.response_times):.2f}",
            "max_response_time_ms": f"{max(self.response_times):.2f}",
            "p95_response_time_ms": f"{sorted(self.response_times)[int(len(self.response_times) * 0.95)]:.2f}",
            "p99_response_time_ms": f"{sorted(self.response_times)[int(len(self.response_times) * 0.99)]:.2f}",
            "total_duration_seconds": f"{self.end_time - self.start_time:.2f}",
            "requests_per_second": f"{self.total_requests / (self.end_time - self.start_time):.2f}",
        }


async def test_health_check():
    """Test that backend is healthy."""
    print("\n=== TEST 1: Health Check ===")
    try:
        response = await CLIENT.get("/health")
        assert (
            response.status_code == 200
        ), f"Health check failed: {response.status_code}"
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ Backend is healthy: {data}")
        return True
    except (httpx.HTTPError, AssertionError, KeyError, ValueError) as error:
        print(f"✗ Health check failed: {error}")
        return False


async def test_order_placement(metrics: PerformanceMetrics):
    """Test order placement workflow."""
    print("\n=== TEST 2: Order Placement Workflow ===")

    order_requests = 10
    success_count = 0

    for i in range(order_requests):
        try:
            start = time.time()
            response = await CLIENT.post(
                "/api/orders",
                json={
                    "symbol": "AAPL",
                    "side": "BUY",
                    "order_type": "MARKET",
                    "quantity": 100.0,
                },
            )
            elapsed = (time.time() - start) * 1000  # Convert to ms

            metrics.record(elapsed)

            if response.status_code == 201:
                data = response.json()
                print(
                    f"  Order {i+1}: {data.get('id', 'N/A')} placed in {elapsed:.2f}ms"
                )
                success_count += 1
            else:
                print(f"  Order {i+1}: Failed with status {response.status_code}")
                metrics.record_failure()

        except (httpx.HTTPError, ValueError) as error:
            print(f"  Order {i+1}: Error - {error}")
            metrics.record_failure()

    print(f"✓ Placed {success_count}/{order_requests} orders successfully")
    return success_count == order_requests


async def test_position_tracking(metrics: PerformanceMetrics):
    """Test position tracking."""
    print("\n=== TEST 3: Position Tracking ===")

    try:
        start = time.time()
        response = await CLIENT.get("/api/positions")
        elapsed = (time.time() - start) * 1000

        metrics.record(elapsed)

        assert response.status_code == 200
        positions = response.json()
        print(f"✓ Retrieved {len(positions)} positions in {elapsed:.2f}ms")
        if positions:
            for pos in positions[:3]:  # Show first 3
                print(
                    f"  - {pos.get('symbol')}: {pos.get('quantity')} @ ${pos.get('entry_price')}"
                )
        return True
    except (httpx.HTTPError, AssertionError, ValueError) as error:
        print(f"✗ Position tracking failed: {error}")
        metrics.record_failure()
        return False


async def test_portfolio_summary(metrics: PerformanceMetrics):
    """Test portfolio summary."""
    print("\n=== TEST 4: Portfolio Summary ===")

    try:
        start = time.time()
        response = await CLIENT.get("/api/portfolio/summary")
        elapsed = (time.time() - start) * 1000

        metrics.record(elapsed)

        assert response.status_code == 200
        summary = response.json()
        print(f"✓ Portfolio Summary (retrieved in {elapsed:.2f}ms):")
        print(f"  - Positions: {summary.get('total_positions')}")
        print(f"  - Realized P&L: ${summary.get('total_realized_pnl')}")
        print(f"  - Unrealized P&L: ${summary.get('total_unrealized_pnl')}")
        return True
    except (httpx.HTTPError, AssertionError, ValueError) as error:
        print(f"✗ Portfolio summary failed: {error}")
        metrics.record_failure()
        return False


async def test_rapid_order_stream(metrics: PerformanceMetrics):
    """Test rapid order submission (load test)."""
    print("\n=== TEST 5: Rapid Order Stream (Load Test) ===")

    rapid_orders = 50
    symbols = ["AAPL", "GOOG", "MSFT", "TSLA"]
    sides = ["BUY", "SELL"]
    success_count = 0

    for i in range(rapid_orders):
        try:
            start = time.time()
            response = await CLIENT.post(
                "/api/orders",
                json={
                    "symbol": symbols[i % len(symbols)],
                    "side": sides[i % len(sides)],
                    "order_type": "MARKET",
                    "quantity": 10.0 + (i % 100),
                },
            )
            elapsed = (time.time() - start) * 1000

            metrics.record(elapsed)

            if response.status_code == 201:
                success_count += 1
            else:
                metrics.record_failure()

            # Show progress every 10 orders
            if (i + 1) % 10 == 0:
                print(f"  Submitted {i+1}/{rapid_orders} orders...")

        except httpx.HTTPError:
            metrics.record_failure()

    success_rate = (success_count / rapid_orders) * 100
    print(
        f"✓ Submitted {success_count}/{rapid_orders} orders ({success_rate:.1f}% success)"
    )
    return success_count > (rapid_orders * 0.9)  # 90% success threshold


async def main():
    """Run all integration tests."""
    print("=" * 70)
    print("HFT TRADING PLATFORM - INTEGRATION TESTS")
    print("=" * 70)
    print(f"Start time: {datetime.now(UTC).isoformat()}")
    print(f"Backend URL: {BASE_URL}")

    metrics = PerformanceMetrics()
    metrics.start()

    try:
        # Run tests in sequence
        results = {}

        results["health"] = await test_health_check()
        if not results["health"]:
            print("\n✗ Backend not healthy, stopping tests")
            return 1

        results["orders"] = await test_order_placement(metrics)
        results["positions"] = await test_position_tracking(metrics)
        results["portfolio"] = await test_portfolio_summary(metrics)
        results["load"] = await test_rapid_order_stream(metrics)

        metrics.stop()

        # Print summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        for test_name, passed in results.items():
            status = "PASSED" if passed else "FAILED"
            print(f"  {test_name.upper():20} {status}")

        print("\n" + "=" * 70)
        print("PERFORMANCE METRICS")
        print("=" * 70)
        summary = metrics.get_summary()
        for key, value in summary.items():
            print(f"  {key:35} {value}")

        print("\n" + "=" * 70)
        print(f"End time: {datetime.now(UTC).isoformat()}")
        print("=" * 70)

        # Overall result
        all_passed = all(results.values())
        if all_passed:
            print("\n✓ ALL TESTS PASSED")
            return 0
        print("\n✗ SOME TESTS FAILED")
        return 1
    finally:
        await CLIENT.aclose()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
