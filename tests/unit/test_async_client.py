"""
Tests for AsyncHTTPClient with comprehensive coverage using respx mocks.
"""

import pytest
import warnings

# Skip all tests if httpx not installed
httpx = pytest.importorskip("httpx")

# Import respx for mocking
try:
    import respx
    from respx import MockRouter
except ImportError:
    pytest.skip("respx is required for these tests", allow_module_level=True)

from src.http_client.async_client import AsyncHTTPClient
from src.http_client.core.config import (
    HTTPClientConfig,
    SecurityConfig,
    TimeoutConfig,
    RetryConfig,
    CircuitBreakerConfig
)
from src.http_client.core.exceptions import (
    TimeoutError,
    ConnectionError,
    TooManyRetriesError,
    CircuitOpenError,
    ServerError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    TooManyRequestsError,
    ResponseTooLargeError,
)
from src.http_client.plugins.plugin import Plugin, PluginPriority
from src.http_client.plugins.async_plugin import AsyncPlugin


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

    def test_init_with_timeout_config(self):
        """Test initialization with TimeoutConfig."""
        timeout_config = TimeoutConfig(connect=5, read=10, total=30)
        client = AsyncHTTPClient(timeout=timeout_config)
        assert client._timeout.connect == 5
        assert client._timeout.read == 10

    def test_init_with_headers(self):
        """Test initialization with custom headers."""
        headers = {"Authorization": "Bearer token123", "X-Custom": "value"}
        client = AsyncHTTPClient(headers=headers)
        assert client._config.headers["Authorization"] == "Bearer token123"
        assert client._config.headers["X-Custom"] == "value"

    def test_init_with_proxies(self):
        """Test initialization with proxies."""
        proxies = {"http://": "http://proxy.example.com:8080"}
        client = AsyncHTTPClient(proxies=proxies)
        assert client._proxies == proxies

    def test_init_with_config(self):
        """Test initialization with HTTPClientConfig."""
        config = HTTPClientConfig.create(
            base_url="https://api.test.com",
            timeout=45,
            max_retries=5
        )
        client = AsyncHTTPClient(config=config)
        assert client.base_url == "https://api.test.com"
        assert client._config.retry.max_attempts == 6  # max_retries + 1

    def test_init_with_plugins(self):
        """Test initialization with plugins."""
        class TestPlugin(AsyncPlugin):
            async def before_request(self, method, url, **kwargs):
                return kwargs
            async def after_response(self, response):
                return response
            async def on_error(self, error, **kwargs):
                pass

        plugin = TestPlugin()
        client = AsyncHTTPClient(plugins=[plugin])
        assert len(client._plugins) == 1
        assert isinstance(client._plugins[0], TestPlugin)

    def test_init_plugins_sorted_by_priority(self):
        """Test that plugins are sorted by priority on initialization."""
        class HighPriorityPlugin(AsyncPlugin):
            priority = PluginPriority.HIGH
            async def before_request(self, method, url, **kwargs):
                return kwargs
            async def after_response(self, response):
                return response
            async def on_error(self, error, **kwargs):
                pass

        class LowPriorityPlugin(AsyncPlugin):
            priority = PluginPriority.LOW
            async def before_request(self, method, url, **kwargs):
                return kwargs
            async def after_response(self, response):
                return response
            async def on_error(self, error, **kwargs):
                pass

        low_plugin = LowPriorityPlugin()
        high_plugin = HighPriorityPlugin()

        # Add in wrong order
        client = AsyncHTTPClient(plugins=[low_plugin, high_plugin])

        # Should be sorted by priority
        assert client._plugins[0].priority < client._plugins[1].priority
        assert isinstance(client._plugins[0], HighPriorityPlugin)
        assert isinstance(client._plugins[1], LowPriorityPlugin)

    def test_init_lazy_client_creation(self):
        """Test that httpx client is not created until needed."""
        client = AsyncHTTPClient(base_url="https://api.example.com")
        assert client._client is None

    def test_init_with_verify_ssl(self):
        """Test initialization with SSL verification settings."""
        client = AsyncHTTPClient(verify_ssl=False)
        assert client._config.security.verify_ssl is False

    def test_init_circuit_breaker_initialized(self):
        """Test that circuit breaker is initialized."""
        client = AsyncHTTPClient()
        assert client._circuit_breaker is not None

    def test_init_retry_engine_initialized(self):
        """Test that retry engine is initialized."""
        client = AsyncHTTPClient()
        assert client._retry_engine is not None


class TestAsyncHTTPClientContextManager:
    """Test async context manager and lifecycle."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        async with AsyncHTTPClient(base_url="https://httpbin.org") as client:
            assert client._client is not None

        # После выхода клиент должен быть закрыт
        assert client._client is None

    @pytest.mark.asyncio
    async def test_manual_close(self):
        """Test manual close."""
        client = AsyncHTTPClient(base_url="https://api.example.com")
        await client._get_client()
        assert client._client is not None

        await client.close()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_double_close_no_error(self):
        """Test that calling close() twice doesn't raise an error."""
        client = AsyncHTTPClient(base_url="https://api.example.com")
        await client._get_client()

        await client.close()
        await client.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_get_client_lazy_initialization(self):
        """Test that _get_client creates client on first call."""
        client = AsyncHTTPClient(base_url="https://api.example.com")
        assert client._client is None

        httpx_client = await client._get_client()
        assert httpx_client is not None
        assert client._client is httpx_client

    @pytest.mark.asyncio
    async def test_get_client_returns_same_instance(self):
        """Test that _get_client returns same client instance."""
        client = AsyncHTTPClient(base_url="https://api.example.com")

        client1 = await client._get_client()
        client2 = await client._get_client()

        assert client1 is client2

    @pytest.mark.asyncio
    async def test_context_manager_creates_client(self):
        """Test that entering context manager creates client."""
        client = AsyncHTTPClient(base_url="https://api.example.com")
        assert client._client is None

        async with client:
            assert client._client is not None

    @pytest.mark.asyncio
    async def test_close_sets_client_to_none(self):
        """Test that close sets _client to None."""
        client = AsyncHTTPClient()
        await client._get_client()
        assert client._client is not None

        await client.close()
        assert client._client is None


class TestAsyncHTTPClientHTTPMethods:
    """Test all HTTP methods with respx mocks."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_request(self):
        """Test GET request with mock."""
        respx.get("https://api.test.com/users").mock(
            return_value=httpx.Response(200, json={"users": ["alice", "bob"]})
        )

        async with AsyncHTTPClient(base_url="https://api.test.com") as client:
            response = await client.get("/users")
            assert response.status_code == 200
            assert response.json() == {"users": ["alice", "bob"]}

    @respx.mock
    @pytest.mark.asyncio
    async def test_post_request(self):
        """Test POST request with mock."""
        respx.post("https://api.test.com/users").mock(
            return_value=httpx.Response(201, json={"id": 1, "name": "alice"})
        )

        async with AsyncHTTPClient(base_url="https://api.test.com") as client:
            response = await client.post("/users", json={"name": "alice"})
            assert response.status_code == 201
            assert response.json()["id"] == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_put_request(self):
        """Test PUT request with mock."""
        respx.put("https://api.test.com/users/1").mock(
            return_value=httpx.Response(200, json={"id": 1, "name": "alice_updated"})
        )

        async with AsyncHTTPClient(base_url="https://api.test.com") as client:
            response = await client.put("/users/1", json={"name": "alice_updated"})
            assert response.status_code == 200
            assert response.json()["name"] == "alice_updated"

    @respx.mock
    @pytest.mark.asyncio
    async def test_patch_request(self):
        """Test PATCH request with mock."""
        respx.patch("https://api.test.com/users/1").mock(
            return_value=httpx.Response(200, json={"id": 1, "email": "alice@example.com"})
        )

        async with AsyncHTTPClient(base_url="https://api.test.com") as client:
            response = await client.patch("/users/1", json={"email": "alice@example.com"})
            assert response.status_code == 200
            assert response.json()["email"] == "alice@example.com"

    @respx.mock
    @pytest.mark.asyncio
    async def test_delete_request(self):
        """Test DELETE request with mock."""
        respx.delete("https://api.test.com/users/1").mock(
            return_value=httpx.Response(204)
        )

        async with AsyncHTTPClient(base_url="https://api.test.com") as client:
            response = await client.delete("/users/1")
            assert response.status_code == 204

    @respx.mock
    @pytest.mark.asyncio
    async def test_head_request(self):
        """Test HEAD request with mock."""
        respx.head("https://api.test.com/users").mock(
            return_value=httpx.Response(200, headers={"Content-Length": "1234"})
        )

        async with AsyncHTTPClient(base_url="https://api.test.com") as client:
            response = await client.head("/users")
            assert response.status_code == 200
            assert response.headers["Content-Length"] == "1234"

    @respx.mock
    @pytest.mark.asyncio
    async def test_options_request(self):
        """Test OPTIONS request with mock."""
        respx.options("https://api.test.com/users").mock(
            return_value=httpx.Response(200, headers={"Allow": "GET, POST, PUT, DELETE"})
        )

        async with AsyncHTTPClient(base_url="https://api.test.com") as client:
            response = await client.options("/users")
            assert response.status_code == 200
            assert "GET" in response.headers["Allow"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_request_with_query_params(self):
        """Test request with query parameters."""
        respx.get("https://api.test.com/users", params={"page": "1", "limit": "10"}).mock(
            return_value=httpx.Response(200, json={"page": 1, "data": []})
        )

        async with AsyncHTTPClient(base_url="https://api.test.com") as client:
            response = await client.get("/users", params={"page": "1", "limit": "10"})
            assert response.status_code == 200

    @respx.mock
    @pytest.mark.asyncio
    async def test_request_with_headers(self):
        """Test request with custom headers."""
        route = respx.get("https://api.test.com/protected").mock(
            return_value=httpx.Response(200, json={"authenticated": True})
        )

        async with AsyncHTTPClient(base_url="https://api.test.com") as client:
            response = await client.get(
                "/protected",
                headers={"Authorization": "Bearer token123"}
            )
            assert response.status_code == 200

    @respx.mock
    @pytest.mark.asyncio
    async def test_request_with_json_data(self):
        """Test request with JSON data."""
        respx.post("https://api.test.com/data").mock(
            return_value=httpx.Response(200, json={"received": True})
        )

        async with AsyncHTTPClient(base_url="https://api.test.com") as client:
            response = await client.post("/data", json={"key": "value", "number": 42})
            assert response.status_code == 200

    @respx.mock
    @pytest.mark.asyncio
    async def test_request_without_base_url(self):
        """Test request with full URL when no base_url set."""
        respx.get("https://api.example.com/test").mock(
            return_value=httpx.Response(200, json={"success": True})
        )

        async with AsyncHTTPClient() as client:
            response = await client.get("https://api.example.com/test")
            assert response.status_code == 200
            assert response.json()["success"] is True


class TestAsyncHTTPClientRequests:
    """Test HTTP requests (integration tests with httpbin - kept for backwards compatibility)."""

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


class TestAsyncHTTPClientRetry:
    """Test retry logic with mocks."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_retry_on_500_error(self):
        """Test that 500 errors trigger retry."""
        # First two requests fail with 500, third succeeds
        route = respx.get("https://api.test.com/unstable").mock(
            side_effect=[
                httpx.Response(500),
                httpx.Response(500),
                httpx.Response(200, json={"success": True})
            ]
        )

        config = HTTPClientConfig.create(max_retries=3)
        async with AsyncHTTPClient(config=config) as client:
            response = await client.get("https://api.test.com/unstable")
            assert response.status_code == 200
            assert response.json()["success"] is True
            # Verify it was called 3 times (2 failures + 1 success)
            assert route.call_count == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_retry_on_502_error(self):
        """Test that 502 errors trigger retry."""
        route = respx.get("https://api.test.com/gateway").mock(
            side_effect=[
                httpx.Response(502),
                httpx.Response(200, json={"ok": True})
            ]
        )

        config = HTTPClientConfig.create(max_retries=2)
        async with AsyncHTTPClient(config=config) as client:
            response = await client.get("https://api.test.com/gateway")
            assert response.status_code == 200
            assert route.call_count == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_retry_on_503_error(self):
        """Test that 503 errors trigger retry."""
        route = respx.get("https://api.test.com/service").mock(
            side_effect=[
                httpx.Response(503),
                httpx.Response(200, json={"available": True})
            ]
        )

        config = HTTPClientConfig.create(max_retries=1)
        async with AsyncHTTPClient(config=config) as client:
            response = await client.get("https://api.test.com/service")
            assert response.status_code == 200

    @respx.mock
    @pytest.mark.asyncio
    async def test_no_retry_on_400_error(self):
        """Test that 400 errors do NOT trigger retry."""
        route = respx.get("https://api.test.com/bad").mock(
            return_value=httpx.Response(400)
        )

        config = HTTPClientConfig.create(max_retries=3)
        async with AsyncHTTPClient(config=config) as client:
            with pytest.raises(BadRequestError):
                await client.get("https://api.test.com/bad")

            # Should only be called once (no retry for 4xx)
            assert route.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_no_retry_on_404_error(self):
        """Test that 404 errors do NOT trigger retry."""
        route = respx.get("https://api.test.com/notfound").mock(
            return_value=httpx.Response(404)
        )

        config = HTTPClientConfig.create(max_retries=3)
        async with AsyncHTTPClient(config=config) as client:
            with pytest.raises(NotFoundError):
                await client.get("https://api.test.com/notfound")

            assert route.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that TooManyRetriesError is raised when max retries exceeded."""
        route = respx.get("https://api.test.com/failing").mock(
            return_value=httpx.Response(500)
        )

        # max_retries=1 means 2 total attempts (1 initial + 1 retry)
        config = HTTPClientConfig.create(max_retries=1)
        async with AsyncHTTPClient(config=config) as client:
            with pytest.raises((TooManyRetriesError, ServerError)):
                await client.get("https://api.test.com/failing")

            # Should be called at least 2 times
            assert route.call_count >= 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_retry_after_header_429(self):
        """Test that 429 with Retry-After header is handled."""
        route = respx.get("https://api.test.com/ratelimit").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "1"}),
                httpx.Response(200, json={"success": True})
            ]
        )

        config = HTTPClientConfig.create(max_retries=2)
        async with AsyncHTTPClient(config=config) as client:
            import time
            start = time.time()
            response = await client.get("https://api.test.com/ratelimit")
            elapsed = time.time() - start

            assert response.status_code == 200
            # Should wait at least 1 second due to Retry-After
            assert elapsed >= 1.0
            assert route.call_count == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_retry_with_connection_error(self):
        """Test retry on connection errors."""
        route = respx.get("https://api.test.com/flaky").mock(
            side_effect=[
                httpx.ConnectError("Connection refused"),
                httpx.Response(200, json={"recovered": True})
            ]
        )

        config = HTTPClientConfig.create(max_retries=2)
        async with AsyncHTTPClient(config=config) as client:
            response = await client.get("https://api.test.com/flaky")
            assert response.status_code == 200
            assert route.call_count == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_retry_with_timeout_error(self):
        """Test retry on timeout errors."""
        route = respx.get("https://api.test.com/slow").mock(
            side_effect=[
                httpx.TimeoutException("Read timeout"),
                httpx.Response(200, json={"ok": True})
            ]
        )

        config = HTTPClientConfig.create(max_retries=2)
        async with AsyncHTTPClient(config=config) as client:
            response = await client.get("https://api.test.com/slow")
            assert response.status_code == 200
            assert route.call_count == 2


class TestAsyncHTTPClientTimeout:
    """Test timeout handling with mocks."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_timeout_error_raised(self):
        """Test that timeout errors are converted to our TimeoutError."""
        respx.get("https://api.test.com/slow").mock(
            side_effect=httpx.TimeoutException("Read timeout")
        )

        config = HTTPClientConfig.create(max_retries=0)
        async with AsyncHTTPClient(config=config) as client:
            # With max_retries=0 and timeout (retryable), expect TooManyRetriesError wrapping TimeoutError
            with pytest.raises((TooManyRetriesError, TimeoutError)):
                await client.get("https://api.test.com/slow")

    @respx.mock
    @pytest.mark.asyncio
    async def test_timeout_with_config(self):
        """Test timeout configuration."""
        timeout_config = TimeoutConfig(connect=5, read=10, total=30)
        client = AsyncHTTPClient(timeout=timeout_config)
        assert client._timeout.connect == 5
        assert client._timeout.read == 10


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

    @respx.mock
    @pytest.mark.asyncio
    async def test_health_check_with_mock(self):
        """Test health check with mock."""
        respx.head("https://api.test.com/health").mock(
            return_value=httpx.Response(200)
        )

        async with AsyncHTTPClient(base_url="https://api.test.com") as client:
            health = await client.health_check(test_url="https://api.test.com/health")

            assert health["healthy"] is True
            assert health["base_url"] == "https://api.test.com"
            assert health["connectivity"]["reachable"] is True
            assert health["connectivity"]["status_code"] == 200

    @respx.mock
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check with connectivity failure."""
        respx.head("https://api.test.com/health").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        async with AsyncHTTPClient() as client:
            health = await client.health_check(test_url="https://api.test.com/health")

            assert health["healthy"] is False
            assert health["connectivity"]["reachable"] is False
            assert health["connectivity"]["error"] is not None


class TestAsyncHTTPClientPlugins:
    """Test plugin functionality (async and sync)."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_plugin_before_request(self):
        """Test that async plugin before_request hook is called."""
        class TestAsyncPlugin(AsyncPlugin):
            def __init__(self):
                self.before_called = False
                self.method = None
                self.url = None

            async def before_request(self, method, url, **kwargs):
                self.before_called = True
                self.method = method
                self.url = url
                # Add custom header
                kwargs.setdefault('headers', {})
                kwargs['headers']['X-Plugin'] = 'TestPlugin'
                return kwargs

        respx.get("https://api.test.com/test").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        plugin = TestAsyncPlugin()
        async with AsyncHTTPClient(base_url="https://api.test.com", plugins=[plugin]) as client:
            await client.get("/test")

            assert plugin.before_called is True
            assert plugin.method == "GET"
            assert "/test" in plugin.url

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_plugin_after_response(self):
        """Test that async plugin after_response hook is called."""
        class TestAsyncPlugin(AsyncPlugin):
            def __init__(self):
                self.after_called = False
                self.response_status = None

            async def after_response(self, response):
                self.after_called = True
                self.response_status = response.status_code
                return response

        respx.get("https://api.test.com/test").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        plugin = TestAsyncPlugin()
        async with AsyncHTTPClient(base_url="https://api.test.com", plugins=[plugin]) as client:
            await client.get("/test")

            assert plugin.after_called is True
            assert plugin.response_status == 200

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_plugin_on_error(self):
        """Test that async plugin on_error hook is called."""
        class TestAsyncPlugin(AsyncPlugin):
            def __init__(self):
                self.error_called = False
                self.error = None

            async def on_error(self, error, **kwargs):
                self.error_called = True
                self.error = error

        respx.get("https://api.test.com/error").mock(
            return_value=httpx.Response(404)
        )

        plugin = TestAsyncPlugin()
        async with AsyncHTTPClient(base_url="https://api.test.com", plugins=[plugin]) as client:
            try:
                await client.get("/error")
            except NotFoundError:
                pass

            assert plugin.error_called is True
            assert isinstance(plugin.error, NotFoundError)

    @respx.mock
    @pytest.mark.asyncio
    async def test_sync_plugin_execution(self):
        """Test that sync plugins are executed via executor."""
        class TestSyncPlugin(Plugin):
            def __init__(self):
                self.before_called = False

            def before_request(self, method, url, **kwargs):
                self.before_called = True
                return kwargs

            def after_response(self, response):
                return response

            def on_error(self, error, **kwargs):
                return False

        respx.get("https://api.test.com/test").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        plugin = TestSyncPlugin()
        async with AsyncHTTPClient(base_url="https://api.test.com", plugins=[plugin]) as client:
            await client.get("/test")

            assert plugin.before_called is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_plugins_execution_order_by_priority(self):
        """Test that plugins execute in priority order."""
        execution_order = []

        class HighPriorityPlugin(AsyncPlugin):
            priority = PluginPriority.HIGH

            async def before_request(self, method, url, **kwargs):
                execution_order.append('high')
                return kwargs

        class LowPriorityPlugin(AsyncPlugin):
            priority = PluginPriority.LOW

            async def before_request(self, method, url, **kwargs):
                execution_order.append('low')
                return kwargs

        class NormalPriorityPlugin(AsyncPlugin):
            priority = PluginPriority.NORMAL

            async def before_request(self, method, url, **kwargs):
                execution_order.append('normal')
                return kwargs

        respx.get("https://api.test.com/test").mock(
            return_value=httpx.Response(200)
        )

        # Add in random order
        plugins = [
            LowPriorityPlugin(),
            HighPriorityPlugin(),
            NormalPriorityPlugin()
        ]

        async with AsyncHTTPClient(base_url="https://api.test.com", plugins=plugins) as client:
            await client.get("/test")

            # Should execute in priority order: high (25) -> normal (50) -> low (75)
            assert execution_order == ['high', 'normal', 'low']

    @respx.mock
    @pytest.mark.asyncio
    async def test_add_plugin_method(self):
        """Test add_plugin method."""
        class TestPlugin(AsyncPlugin):
            async def before_request(self, method, url, **kwargs):
                return kwargs

        respx.get("https://api.test.com/test").mock(
            return_value=httpx.Response(200)
        )

        async with AsyncHTTPClient(base_url="https://api.test.com") as client:
            assert len(client._plugins) == 0

            plugin = TestPlugin()
            client.add_plugin(plugin)

            assert len(client._plugins) == 1
            assert plugin in client._plugins

    @respx.mock
    @pytest.mark.asyncio
    async def test_remove_plugin_method(self):
        """Test remove_plugin method."""
        class TestPlugin(AsyncPlugin):
            async def before_request(self, method, url, **kwargs):
                return kwargs

        plugin = TestPlugin()
        async with AsyncHTTPClient(base_url="https://api.test.com", plugins=[plugin]) as client:
            assert len(client._plugins) == 1

            client.remove_plugin(plugin)

            assert len(client._plugins) == 0
            assert plugin not in client._plugins

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_plugins_order(self):
        """Test get_plugins_order method."""
        class HighPlugin(AsyncPlugin):
            priority = PluginPriority.HIGH

        class LowPlugin(AsyncPlugin):
            priority = PluginPriority.LOW

        high = HighPlugin()
        low = LowPlugin()

        client = AsyncHTTPClient(plugins=[low, high])
        order = client.get_plugins_order()

        assert len(order) == 2
        assert order[0] == ('HighPlugin', PluginPriority.HIGH)
        assert order[1] == ('LowPlugin', PluginPriority.LOW)

    @respx.mock
    @pytest.mark.asyncio
    async def test_plugin_error_does_not_break_request(self):
        """Test that plugin errors don't break the request."""
        class BrokenPlugin(AsyncPlugin):
            async def before_request(self, method, url, **kwargs):
                raise ValueError("Plugin error!")

        respx.get("https://api.test.com/test").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        plugin = BrokenPlugin()
        async with AsyncHTTPClient(base_url="https://api.test.com", plugins=[plugin]) as client:
            # Request should succeed despite plugin error
            with warnings.catch_warnings(record=True):
                response = await client.get("/test")
                assert response.status_code == 200


class TestAsyncHTTPClientErrors:
    """Test error handling with mocks."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_400_bad_request_error(self):
        """Test 400 Bad Request error."""
        respx.get("https://api.test.com/bad").mock(
            return_value=httpx.Response(400)
        )

        async with AsyncHTTPClient(base_url="https://api.test.com") as client:
            with pytest.raises(BadRequestError) as exc_info:
                await client.get("/bad")

            assert exc_info.value.status_code == 400

    @respx.mock
    @pytest.mark.asyncio
    async def test_401_unauthorized_error(self):
        """Test 401 Unauthorized error."""
        respx.get("https://api.test.com/protected").mock(
            return_value=httpx.Response(401)
        )

        async with AsyncHTTPClient(base_url="https://api.test.com") as client:
            with pytest.raises(UnauthorizedError) as exc_info:
                await client.get("/protected")

            assert exc_info.value.status_code == 401

    @respx.mock
    @pytest.mark.asyncio
    async def test_403_forbidden_error(self):
        """Test 403 Forbidden error."""
        respx.get("https://api.test.com/forbidden").mock(
            return_value=httpx.Response(403)
        )

        async with AsyncHTTPClient(base_url="https://api.test.com") as client:
            with pytest.raises(ForbiddenError) as exc_info:
                await client.get("/forbidden")

            assert exc_info.value.status_code == 403

    @respx.mock
    @pytest.mark.asyncio
    async def test_404_not_found_error(self):
        """Test 404 Not Found error."""
        respx.get("https://api.test.com/notfound").mock(
            return_value=httpx.Response(404)
        )

        async with AsyncHTTPClient(base_url="https://api.test.com") as client:
            with pytest.raises(NotFoundError) as exc_info:
                await client.get("/notfound")

            assert exc_info.value.status_code == 404

    @respx.mock
    @pytest.mark.asyncio
    async def test_429_too_many_requests_error(self):
        """Test 429 Too Many Requests error."""
        respx.get("https://api.test.com/ratelimit").mock(
            return_value=httpx.Response(429, headers={"Retry-After": "60"})
        )

        config = HTTPClientConfig.create(max_retries=0)
        async with AsyncHTTPClient(config=config) as client:
            # With max_retries=0 and 429 (retryable), expect TooManyRetriesError wrapping TooManyRequestsError
            with pytest.raises((TooManyRetriesError, TooManyRequestsError)):
                await client.get("https://api.test.com/ratelimit")

    @respx.mock
    @pytest.mark.asyncio
    async def test_500_server_error(self):
        """Test 500 Server Error."""
        respx.get("https://api.test.com/error").mock(
            return_value=httpx.Response(500)
        )

        config = HTTPClientConfig.create(max_retries=0)
        async with AsyncHTTPClient(config=config) as client:
            with pytest.raises(ServerError) as exc_info:
                await client.get("https://api.test.com/error")

            assert exc_info.value.status_code == 500

    @respx.mock
    @pytest.mark.asyncio
    async def test_connection_error(self):
        """Test connection error."""
        respx.get("https://api.test.com/connect").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        config = HTTPClientConfig.create(max_retries=0)
        async with AsyncHTTPClient(config=config) as client:
            # With max_retries=0 and connection error (retryable), expect TooManyRetriesError wrapping ConnectionError
            with pytest.raises((TooManyRetriesError, ConnectionError)):
                await client.get("https://api.test.com/connect")

    @respx.mock
    @pytest.mark.asyncio
    async def test_response_too_large_error(self):
        """Test ResponseTooLargeError on large content."""
        respx.get("https://api.test.com/large").mock(
            return_value=httpx.Response(
                200,
                headers={"Content-Length": "999999999"}  # Very large
            )
        )

        config = HTTPClientConfig.create()
        config = HTTPClientConfig(
            base_url=config.base_url,
            headers=config.headers,
            proxies=config.proxies,
            timeout=config.timeout,
            retry=config.retry,
            pool=config.pool,
            security=SecurityConfig(max_response_size=1000),  # Small limit
            circuit_breaker=config.circuit_breaker,
            logging=config.logging
        )

        async with AsyncHTTPClient(config=config) as client:
            with pytest.raises(ResponseTooLargeError) as exc_info:
                await client.get("https://api.test.com/large")

            assert exc_info.value.size == 999999999


class TestAsyncHTTPClientEdgeCases:
    """Test edge cases."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_empty_base_url(self):
        """Test with empty base_url."""
        respx.get("https://api.test.com/test").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        async with AsyncHTTPClient(base_url="") as client:
            response = await client.get("https://api.test.com/test")
            assert response.status_code == 200

    @respx.mock
    @pytest.mark.asyncio
    async def test_none_base_url(self):
        """Test with None base_url."""
        respx.get("https://api.test.com/test").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        async with AsyncHTTPClient(base_url=None) as client:
            response = await client.get("https://api.test.com/test")
            assert response.status_code == 200

    @respx.mock
    @pytest.mark.asyncio
    async def test_binary_response(self):
        """Test binary response data."""
        binary_data = b'\x00\x01\x02\x03\x04\x05'
        respx.get("https://api.test.com/binary").mock(
            return_value=httpx.Response(200, content=binary_data)
        )

        async with AsyncHTTPClient(base_url="https://api.test.com") as client:
            response = await client.get("/binary")
            assert response.content == binary_data

    @respx.mock
    @pytest.mark.asyncio
    async def test_custom_headers_passed(self):
        """Test that custom headers are passed correctly."""
        route = respx.get("https://api.test.com/test").mock(
            return_value=httpx.Response(200)
        )

        headers = {"X-Custom-Header": "CustomValue", "User-Agent": "MyApp/1.0"}
        async with AsyncHTTPClient(base_url="https://api.test.com", headers=headers) as client:
            await client.get("/test")

            # Headers should be in client config
            assert client._config.headers["X-Custom-Header"] == "CustomValue"

    @respx.mock
    @pytest.mark.asyncio
    async def test_proxies_configuration(self):
        """Test proxies configuration."""
        proxies = {
            "http://": "http://proxy.example.com:8080",
            "https://": "http://proxy.example.com:8080"
        }

        client = AsyncHTTPClient(proxies=proxies)
        assert client._proxies == proxies

    @respx.mock
    @pytest.mark.asyncio
    async def test_multiple_requests_same_client(self):
        """Test multiple requests with same client instance."""
        respx.get("https://api.test.com/1").mock(
            return_value=httpx.Response(200, json={"id": 1})
        )
        respx.get("https://api.test.com/2").mock(
            return_value=httpx.Response(200, json={"id": 2})
        )
        respx.get("https://api.test.com/3").mock(
            return_value=httpx.Response(200, json={"id": 3})
        )

        async with AsyncHTTPClient(base_url="https://api.test.com") as client:
            r1 = await client.get("/1")
            r2 = await client.get("/2")
            r3 = await client.get("/3")

            assert r1.json()["id"] == 1
            assert r2.json()["id"] == 2
            assert r3.json()["id"] == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_base_url_property(self):
        """Test base_url property."""
        client = AsyncHTTPClient(base_url="https://api.test.com")
        assert client.base_url == "https://api.test.com"

    @respx.mock
    @pytest.mark.asyncio
    async def test_response_without_json(self):
        """Test handling response without JSON."""
        respx.get("https://api.test.com/text").mock(
            return_value=httpx.Response(200, text="Plain text response")
        )

        async with AsyncHTTPClient(base_url="https://api.test.com") as client:
            response = await client.get("/text")
            assert response.text == "Plain text response"


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
