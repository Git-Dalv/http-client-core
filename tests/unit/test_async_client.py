"""
Tests for AsyncHTTPClient.
"""

import pytest

# Skip all tests if httpx not installed
httpx = pytest.importorskip("httpx")

from src.http_client.async_client import AsyncHTTPClient
from src.http_client.core.config import HTTPClientConfig, SecurityConfig


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


class TestAsyncHTTPClientDownload:
    """Test async download method."""

    @pytest.mark.asyncio
    async def test_download_basic(self, tmp_path):
        """Test basic file download."""
        import os

        output_file = tmp_path / "test_file.txt"

        async with AsyncHTTPClient() as client:
            # Download a small file
            bytes_downloaded = await client.download(
                "https://httpbin.org/bytes/1024",
                str(output_file)
            )

            assert bytes_downloaded == 1024
            assert os.path.exists(output_file)
            assert os.path.getsize(output_file) == 1024

    @pytest.mark.asyncio
    async def test_download_with_progress_callback(self, tmp_path):
        """Test download with progress callback."""
        output_file = tmp_path / "test_file.txt"
        progress_calls = []

        def on_progress(downloaded, total):
            progress_calls.append((downloaded, total))

        async with AsyncHTTPClient() as client:
            await client.download(
                "https://httpbin.org/bytes/2048",
                str(output_file),
                progress_callback=on_progress
            )

            # Verify progress was tracked
            assert len(progress_calls) > 0
            # Last call should have total bytes
            last_downloaded, last_total = progress_calls[-1]
            assert last_downloaded == 2048

    @pytest.mark.asyncio
    async def test_download_custom_chunk_size(self, tmp_path):
        """Test download with custom chunk size."""
        output_file = tmp_path / "test_file.txt"

        async with AsyncHTTPClient() as client:
            bytes_downloaded = await client.download(
                "https://httpbin.org/bytes/4096",
                str(output_file),
                chunk_size=1024
            )

            assert bytes_downloaded == 4096

    @pytest.mark.asyncio
    async def test_download_size_limit_exceeded(self, tmp_path):
        """Test that download fails when size exceeds limit."""
        from src.http_client.core.exceptions import ResponseTooLargeError
        from src.http_client.core.config import HTTPClientConfig, SecurityConfig

        output_file = tmp_path / "test_file.txt"

        # Create client with very small size limit
        config = HTTPClientConfig.create(
            verify_ssl=True
        )
        config = HTTPClientConfig(
            base_url=config.base_url,
            headers=config.headers,
            proxies=config.proxies,
            timeout=config.timeout,
            retry=config.retry,
            pool=config.pool,
            security=SecurityConfig(max_response_size=100),  # Only 100 bytes
            circuit_breaker=config.circuit_breaker,
            logging=config.logging
        )

        async with AsyncHTTPClient(config=config) as client:
            with pytest.raises(ResponseTooLargeError) as exc_info:
                await client.download(
                    "https://httpbin.org/bytes/1024",
                    str(output_file)
                )

            # Verify file was cleaned up
            import os
            assert not os.path.exists(output_file)

    @pytest.mark.asyncio
    async def test_download_http_error(self, tmp_path):
        """Test download handles HTTP errors."""
        import httpx

        output_file = tmp_path / "test_file.txt"

        async with AsyncHTTPClient() as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.download(
                    "https://httpbin.org/status/404",
                    str(output_file)
                )

            # Verify file was cleaned up
            import os
            assert not os.path.exists(output_file)

    @pytest.mark.asyncio
    async def test_download_cleanup_on_error(self, tmp_path):
        """Test that partial file is cleaned up on error."""
        from src.http_client.core.exceptions import ResponseTooLargeError
        from src.http_client.core.config import HTTPClientConfig, SecurityConfig
        import os

        output_file = tmp_path / "test_file.txt"

        # Create client with size limit that will be exceeded mid-download
        config = HTTPClientConfig.create(verify_ssl=True)
        config = HTTPClientConfig(
            base_url=config.base_url,
            headers=config.headers,
            proxies=config.proxies,
            timeout=config.timeout,
            retry=config.retry,
            pool=config.pool,
            security=SecurityConfig(max_response_size=512),  # Will fail mid-download
            circuit_breaker=config.circuit_breaker,
            logging=config.logging
        )

        async with AsyncHTTPClient(config=config) as client:
            with pytest.raises(ResponseTooLargeError):
                await client.download(
                    "https://httpbin.org/bytes/2048",
                    str(output_file),
                    chunk_size=256
                )

            # Verify partial file was removed
            assert not os.path.exists(output_file)

    @pytest.mark.asyncio
    async def test_download_returns_bytes_downloaded(self, tmp_path):
        """Test that download returns correct byte count."""
        output_file = tmp_path / "test_file.txt"

        async with AsyncHTTPClient() as client:
            bytes_downloaded = await client.download(
                "https://httpbin.org/bytes/512",
                str(output_file)
            )

            assert isinstance(bytes_downloaded, int)
            assert bytes_downloaded == 512


class TestAsyncHTTPClientCircuitBreaker:
    """Test circuit breaker functionality."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_initialization(self):
        """Test that circuit breaker is initialized."""
        from src.http_client.core.config import CircuitBreakerConfig

        config = HTTPClientConfig.create()
        async with AsyncHTTPClient(config=config) as client:
            assert client._circuit_breaker is not None
            state = await client._circuit_breaker.get_state()
            from src.http_client.core.circuit_breaker import CircuitState
            assert state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """Test that circuit breaker opens after reaching failure threshold."""
        from src.http_client.core.config import CircuitBreakerConfig
        from src.http_client.core.exceptions import CircuitOpenError, ServerError

        # Configure circuit breaker with low threshold
        cb_config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=3,  # Open after 3 failures
            recovery_timeout=60.0
        )
        config = HTTPClientConfig.create()
        config = HTTPClientConfig(
            base_url=config.base_url,
            headers=config.headers,
            proxies=config.proxies,
            timeout=config.timeout,
            retry=config.retry,
            pool=config.pool,
            security=config.security,
            circuit_breaker=cb_config,
            logging=config.logging
        )

        async with AsyncHTTPClient(config=config) as client:
            # Make 3 failing requests to open the circuit
            for _ in range(3):
                try:
                    # Use a URL that will fail
                    await client.get("https://httpbin.org/status/500")
                except ServerError:
                    pass  # Expected

            # Circuit should now be open
            from src.http_client.core.circuit_breaker import CircuitState
            state = await client._circuit_breaker.get_state()
            assert state == CircuitState.OPEN

            # Next request should fail with CircuitOpenError
            with pytest.raises(CircuitOpenError) as exc_info:
                await client.get("https://httpbin.org/get")

            assert "Circuit breaker is OPEN" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_success(self):
        """Test that circuit breaker records successful requests."""
        from src.http_client.core.config import CircuitBreakerConfig

        cb_config = CircuitBreakerConfig(enabled=True, failure_threshold=5)
        config = HTTPClientConfig.create()
        config = HTTPClientConfig(
            base_url=config.base_url,
            headers=config.headers,
            proxies=config.proxies,
            timeout=config.timeout,
            retry=config.retry,
            pool=config.pool,
            security=config.security,
            circuit_breaker=cb_config,
            logging=config.logging
        )

        async with AsyncHTTPClient(config=config) as client:
            # Successful request
            response = await client.get("https://httpbin.org/get")
            assert response.status_code == 200

            # Circuit should remain closed
            from src.http_client.core.circuit_breaker import CircuitState
            state = await client._circuit_breaker.get_state()
            assert state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_disabled(self):
        """Test that circuit breaker can be disabled."""
        from src.http_client.core.config import CircuitBreakerConfig

        cb_config = CircuitBreakerConfig(enabled=False)
        config = HTTPClientConfig.create()
        config = HTTPClientConfig(
            base_url=config.base_url,
            headers=config.headers,
            proxies=config.proxies,
            timeout=config.timeout,
            retry=config.retry,
            pool=config.pool,
            security=config.security,
            circuit_breaker=cb_config,
            logging=config.logging
        )

        async with AsyncHTTPClient(config=config) as client:
            # Even with many failures, circuit should stay closed
            for _ in range(10):
                try:
                    await client.get("https://httpbin.org/status/500")
                except:
                    pass

            # Circuit should remain closed (disabled)
            from src.http_client.core.circuit_breaker import CircuitState
            state = await client._circuit_breaker.get_state()
            assert state == CircuitState.CLOSED
