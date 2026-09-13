#!/usr/bin/env python3
# trading-platform-orchestration/scripts/distributed_load_test.py
# Kubernetes distributed load testing
# Each pod sends orders independently, results aggregated

import asyncio
import json
import os
import statistics
import sys
import time

import httpx


class LoadTestClient:
    """Single load test client (one pod in Kubernetes)"""

    def __init__(self, client_id: int, api_url: str, duration_sec: int = 60):
        self.client_id = client_id
        self.api_url = api_url
        self.duration_sec = duration_sec

        self.orders_sent = 0
        self.orders_success = 0
        self.latencies: list[float] = []
        self.errors = 0

    async def run(self):
        """Run load test for this client"""
        # Create user
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                # Register unique user
                reg = await client.post(
                    f"{self.api_url}/api/auth/register",
                    json={
                        "username": f"client_{self.client_id}_{int(time.time())}",
                        "email": f"client_{self.client_id}_{int(time.time())}@test.com",
                        "password": "Pass123!",
                    },
                    timeout=10,
                )

                if reg.status_code != 201:
                    print(
                        f"[Client {self.client_id}] Failed to register", file=sys.stderr
                    )
                    return

                token = reg.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}

                # Submit orders for duration
                start = time.perf_counter()
                end = start + self.duration_sec

                while time.perf_counter() < end:
                    try:
                        req_start = time.perf_counter()
                        resp = await client.post(
                            f"{self.api_url}/api/orders",
                            json={
                                "symbol": "AAPL",
                                "side": (
                                    "BUY" if self.orders_sent % 2 == 0 else "SELL"
                                ),
                                "order_type": "MARKET",
                                "quantity": 100.0,
                                "price": 150.0,
                            },
                            headers=headers,
                            timeout=5,
                        )

                        latency = (time.perf_counter() - req_start) * 1000
                        self.latencies.append(latency)
                        self.orders_sent += 1

                        if resp.status_code in (200, 201):
                            self.orders_success += 1

                    except httpx.HTTPError:
                        self.errors += 1

                # Print results for this client
                elapsed = time.perf_counter() - start
                throughput = self.orders_sent / elapsed

                print(f"[Client {self.client_id}]")
                print(f"  Orders: {self.orders_sent}")
                print(f"  Throughput: {throughput:.0f} orders/sec")
                success_rate = (
                    (self.orders_success / self.orders_sent) * 100
                    if self.orders_sent
                    else 0
                )
                print(f"  Success rate: {success_rate:.1f}%")
                if self.latencies:
                    self.latencies.sort()
                    print(
                        f"  Latency: {statistics.mean(self.latencies):.2f}ms avg, "
                        f"{self.latencies[-1]:.2f}ms max"
                    )

                # Output JSON for aggregation
                result = {
                    "client_id": self.client_id,
                    "orders_sent": self.orders_sent,
                    "orders_success": self.orders_success,
                    "throughput": throughput,
                    "avg_latency": (
                        statistics.mean(self.latencies) if self.latencies else 0
                    ),
                    "max_latency": max(self.latencies) if self.latencies else 0,
                }
                print(f"JSON:{json.dumps(result)}")

            except (httpx.HTTPError, KeyError, ValueError) as error:
                print(f"[Client {self.client_id}] Error: {error!s}", file=sys.stderr)
                self.errors += 1


async def main():
    # Get config from environment
    api_url = os.getenv("API_URL", "http://localhost:8000")
    client_id = int(os.getenv("CLIENT_ID", "0"))
    duration_sec = int(os.getenv("DURATION_SEC", "60"))

    print(f"Starting load test client {client_id}")
    print(f"API URL: {api_url}")
    print(f"Duration: {duration_sec} seconds")
    print("=" * 60)

    client = LoadTestClient(client_id, api_url, duration_sec)
    await client.run()


if __name__ == "__main__":
    asyncio.run(main())
