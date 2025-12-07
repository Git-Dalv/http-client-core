"""
Tests for AsyncHTTPClient.
"""

import pytest

# Skip all tests if httpx not installed
httpx = pytest.importorskip("httpx")

from src.http_client.async_client import AsyncHTTPClient


class TestAsyncHTTPClientInit:
    """Test AsyncHTTPClient initialization."""

    def test_init_with_base_url(self):
        """Test initialization with base_url."""
        client = AsyncHTTPClient(base_url="https://api.example.com")
        assert client.base_url == "https://api.example.com"

    def test_init_with_timeout(self):
        """Test initialization with timeout."""
        client = AsyncHTTPClient(timeout=60)
        assert client._timeout.connect == 60


class TestAsyncHTTPClientContextManager:
    """Test async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        async with AsyncHTTPClient(base_url="https://httpbin.org") as client:
            assert client._client is not None

        # После выхода клиент должен быть закрыт
        assert client._client is None


class TestAsyncHTTPClientRequests:
    """Test HTTP requests."""

    @pytest.mark.asyncio
    async def test_get_request(self):
        """Test GET request."""
        async with AsyncHTTPClient(base_url="https://httpbin.org") as client:
            response = await client.get("/get")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_post_request(self):
        """Test POST request."""
        async with AsyncHTTPClient(base_url="https://httpbin.org") as client:
            response = await client.post("/post", json={"key": "value"})
            assert response.status_code == 200
            data = response.json()
            assert data["json"]["key"] == "value"


class TestAsyncHTTPClientHealthCheck:
    """Test health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_basic(self):
        """Test basic health check."""
        client = AsyncHTTPClient(base_url="https://httpbin.org")

        health = await client.health_check()

        assert health["healthy"] is True
        assert health["client_type"] == "async"
        await client.close()

    @pytest.mark.asyncio
    async def test_health_check_with_url(self):
        """Test health check with connectivity test."""
        async with AsyncHTTPClient() as client:
            health = await client.health_check(test_url="https://httpbin.org/get")

            assert health["connectivity"]["reachable"] is True
            assert health["connectivity"]["status_code"] == 200
