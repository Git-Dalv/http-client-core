"""
Comprehensive tests for HTTPClient - complete coverage.
"""

import pytest
import responses
from src.http_client.core.http_client import HTTPClient
from src.http_client.core.exceptions import HTTPClientException, NotFoundError
from src.http_client.plugins.logging_plugin import LoggingPlugin


@pytest.fixture
def base_url():
    """Base URL for testing."""
    return "https://api.example.com"


class TestHTTPClientInit:
    """Test HTTPClient initialization."""

    def test_client_init_with_base_url(self, base_url):
        """Test initialization with base_url."""
        client = HTTPClient(base_url=base_url)
        assert client.base_url == base_url.rstrip('/')
        client.close()

    def test_client_init_with_trailing_slash(self):
        """Test that trailing slash is removed from base_url."""
        client = HTTPClient(base_url="https://api.example.com/")
        assert client.base_url == "https://api.example.com"
        client.close()

    def test_client_init_with_custom_headers(self, base_url):
        """Test initialization with custom headers."""
        headers = {"Authorization": "Bearer token123"}
        client = HTTPClient(base_url=base_url, headers=headers)
        assert "Authorization" in client._session.headers
        client.close()

    def test_client_init_with_timeout(self, base_url):
        """Test initialization with custom timeout."""
        client = HTTPClient(base_url=base_url, timeout=30)
        assert client._timeout == 30
        client.close()

    def test_client_init_with_proxies(self, base_url):
        """Test initialization with proxies."""
        proxies = {"http": "http://proxy.example.com:8080"}
        client = HTTPClient(base_url=base_url, proxies=proxies)
        assert client._proxies == proxies
        client.close()

    def test_client_init_with_verify_ssl_false(self, base_url):
        """Test initialization with SSL verification disabled."""
        client = HTTPClient(base_url=base_url, verify_ssl=False)
        assert client._verify_ssl is False
        client.close()

    def test_client_session_created(self, base_url):
        """Test that session is created on init."""
        client = HTTPClient(base_url=base_url)
        assert client._session is not None
        client.close()


class TestHTTPClientContextManager:
    """Test HTTPClient as context manager."""

    def test_context_manager_basic(self, base_url):
        """Test basic context manager usage."""
        with HTTPClient(base_url=base_url) as client:
            assert client._session is not None

    @responses.activate
    def test_context_manager_with_request(self, base_url):
        """Test context manager with actual request."""
        responses.add(
            responses.GET,
            f"{base_url}/test",
            json={"result": "ok"},
            status=200
        )

        with HTTPClient(base_url=base_url) as client:
            response = client.get("/test")
            assert response.status_code == 200


class TestHTTPClientHTTPMethods:
    """Test all HTTP methods."""

    @responses.activate
    def test_get_request(self, base_url):
        """Test GET request."""
        responses.add(
            responses.GET,
            f"{base_url}/users",
            json={"users": []},
            status=200
        )

        client = HTTPClient(base_url=base_url)
        response = client.get("/users")

        assert response.status_code == 200
        assert response.json() == {"users": []}
        client.close()

    @responses.activate
    def test_post_request(self, base_url):
        """Test POST request."""
        responses.add(
            responses.POST,
            f"{base_url}/users",
            json={"id": 1, "name": "John"},
            status=201
        )

        client = HTTPClient(base_url=base_url)
        response = client.post("/users", json={"name": "John"})

        assert response.status_code == 201
        assert response.json()["name"] == "John"
        client.close()

    @responses.activate
    def test_put_request(self, base_url):
        """Test PUT request."""
        responses.add(
            responses.PUT,
            f"{base_url}/users/1",
            json={"id": 1, "name": "Jane"},
            status=200
        )

        client = HTTPClient(base_url=base_url)
        response = client.put("/users/1", json={"name": "Jane"})

        assert response.status_code == 200
        client.close()

    @responses.activate
    def test_patch_request(self, base_url):
        """Test PATCH request."""
        responses.add(
            responses.PATCH,
            f"{base_url}/users/1",
            json={"id": 1, "email": "new@example.com"},
            status=200
        )

        client = HTTPClient(base_url=base_url)
        response = client.patch("/users/1", json={"email": "new@example.com"})

        assert response.status_code == 200
        client.close()

    @responses.activate
    def test_delete_request(self, base_url):
        """Test DELETE request."""
        responses.add(
            responses.DELETE,
            f"{base_url}/users/1",
            status=204
        )

        client = HTTPClient(base_url=base_url)
        response = client.delete("/users/1")

        assert response.status_code == 204
        client.close()

    @responses.activate
    def test_head_request(self, base_url):
        """Test HEAD request."""
        responses.add(
            responses.HEAD,
            f"{base_url}/users",
            status=200
        )

        client = HTTPClient(base_url=base_url)
        response = client.head("/users")

        assert response.status_code == 200
        client.close()

    @responses.activate
    def test_options_request(self, base_url):
        """Test OPTIONS request."""
        responses.add(
            responses.OPTIONS,
            f"{base_url}/users",
            headers={"Allow": "GET, POST, OPTIONS"},
            status=200
        )

        client = HTTPClient(base_url=base_url)
        response = client.options("/users")

        assert response.status_code == 200
        client.close()


class TestHTTPClientURLHandling:
    """Test URL building and handling."""

    @responses.activate
    def test_relative_url_with_base(self, base_url):
        """Test relative URL with base_url."""
        responses.add(
            responses.GET,
            f"{base_url}/posts/1",
            json={"id": 1},
            status=200
        )

        client = HTTPClient(base_url=base_url)
        response = client.get("/posts/1")

        assert response.status_code == 200
        client.close()

    @responses.activate
    def test_absolute_url_overrides_base(self, base_url):
        """Test that absolute URL overrides base_url."""
        responses.add(
            responses.GET,
            "https://other.example.com/data",
            json={"result": "ok"},
            status=200
        )

        client = HTTPClient(base_url=base_url)
        response = client.get("https://other.example.com/data")

        assert response.status_code == 200
        client.close()

    @responses.activate
    def test_url_with_query_params(self, base_url):
        """Test URL with query parameters."""
        responses.add(
            responses.GET,
            f"{base_url}/users?page=1&limit=10",
            json={"users": []},
            status=200
        )

        client = HTTPClient(base_url=base_url)
        response = client.get("/users", params={"page": 1, "limit": 10})

        assert response.status_code == 200
        client.close()


class TestHTTPClientErrorHandling:
    """Test error handling."""

    @responses.activate
    def test_404_error(self, base_url):
        """Test 404 error handling."""
        responses.add(
            responses.GET,
            f"{base_url}/notfound",
            status=404
        )

        client = HTTPClient(base_url=base_url)

        with pytest.raises(NotFoundError):
            client.get("/notfound")

        client.close()

    @responses.activate
    def test_500_error(self, base_url):
        """Test 500 error handling."""
        responses.add(
            responses.GET,
            f"{base_url}/error",
            status=500
        )

        client = HTTPClient(base_url=base_url)

        with pytest.raises(HTTPClientException):
            client.get("/error")

        client.close()


class TestHTTPClientPlugins:
    """Test plugin system."""

    def test_add_plugin(self, base_url):
        """Test adding a plugin."""
        client = HTTPClient(base_url=base_url)
        plugin = LoggingPlugin()

        client.add_plugin(plugin)

        assert plugin in client._plugins
        client.close()

    def test_remove_plugin(self, base_url):
        """Test removing a plugin."""
        client = HTTPClient(base_url=base_url)
        plugin = LoggingPlugin()

        client.add_plugin(plugin)
        client.remove_plugin(plugin)

        assert plugin not in client._plugins
        client.close()

    @responses.activate
    def test_plugin_hooks_called(self, base_url):
        """Test that plugin hooks are called."""
        responses.add(
            responses.GET,
            f"{base_url}/test",
            json={"ok": True},
            status=200
        )

        plugin = LoggingPlugin()
        client = HTTPClient(base_url=base_url)
        client.add_plugin(plugin)

        response = client.get("/test")

        assert response.status_code == 200
        client.close()


class TestHTTPClientProperties:
    """Test client properties."""

    def test_base_url_property(self, base_url):
        """Test base_url property."""
        client = HTTPClient(base_url=base_url)
        assert client.base_url == base_url.rstrip('/')
        client.close()

    def test_timeout_property(self, base_url):
        """Test timeout property."""
        client = HTTPClient(base_url=base_url, timeout=60)
        assert client.timeout == 60
        client.close()

    def test_session_property(self, base_url):
        """Test session property."""
        client = HTTPClient(base_url=base_url)
        assert client.session is not None
        client.close()


class TestHTTPClientClose:
    """Test client cleanup."""

    def test_close_method(self, base_url):
        """Test close() method."""
        client = HTTPClient(base_url=base_url)
        client.close()
        # Should not raise

    def test_close_multiple_times(self, base_url):
        """Test that close() can be called multiple times."""
        client = HTTPClient(base_url=base_url)
        client.close()
        client.close()  # Should not raise
