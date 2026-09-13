# tests/conftest.py
# Pytest configuration and fixtures for integration tests
# Provides: gRPC client, API client, test data fixtures

import asyncio

import grpc
import pytest
from httpx import AsyncClient

# Configuration
GRPC_TARGET = "localhost:50051"
API_TARGET = "http://localhost:8000"
TIMEOUT = 10


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def api_client():
    """Create FastAPI test client."""
    async with AsyncClient(base_url=API_TARGET, timeout=TIMEOUT) as client:
        yield client


@pytest.fixture
def grpc_channel():
    """Create gRPC channel to trading engine."""
    channel = grpc.aio.secure_channel(GRPC_TARGET, grpc.ssl_channel_credentials())
    yield channel
    channel.close()


@pytest.fixture
def sample_order():
    """Sample market order for testing."""
    return {
        "symbol": "AAPL",
        "side": "BUY",
        "type": "MARKET",
        "quantity": 100,
        "price": 150.00,
    }


@pytest.fixture
def sample_limit_order():
    """Sample limit order for testing."""
    return {
        "symbol": "MSFT",
        "side": "SELL",
        "type": "LIMIT",
        "quantity": 50,
        "price": 375.50,
    }
