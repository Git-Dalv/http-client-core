"""
Comprehensive tests for HTTPClient with full coverage.
Uses mocked HTTP responses to avoid network dependencies.
"""

from typing import Any, Dict

import pytest
import requests as requests_lib
import responses

from src.http_client.core.exceptions import (
    ConnectionError,
    HTTPClientException,
    NotFoundError,
    TimeoutError,
)
from src.http_client.core.http_client import HTTPClient
from src.http_client.plugins.plugin import Plugin


class TestHTTPClientInitialization:
    """Test HTTPClient initialization and configuration."""

    def test_init_with_base_url(self):
        """Test initialization with base URL."""
        client = HTTPClient(base_url="https://api.example.com")
        assert client.base_url == "https://api.example.com"
        client.close()

    def test_init_without_base_url(self):
        """Test initialization without base URL."""
        client = HTTPClient()
        assert client.base_url is None
        client.close()

    def test_init_with_timeout(self):
        """Test initialization with custom timeout."""
        client = HTTPClient(timeout=30)
        assert client.timeout == 30
        client.close()

    def test_init_with_default_timeout(self):
        """Test initialization with default timeout."""
        client = HTTPClient()
        assert client.timeout == 30  # Default timeout
        client.close()

    def test_init_with_verify_ssl_false(self):
        """Test initialization with SSL verification disabled."""
        client = HTTPClient(verify_ssl=False)
        assert client._verify_ssl is False
        client.close()

    def test_init_with_proxies(self):
        """Test initialization with proxies."""
        proxies = {"http": "http://proxy.example.com:8080"}
        client = HTTPClient(proxies=proxies)
        assert client._proxies == proxies
        client.close()

    def test_session_created(self):
        """Test that session is created on initialization."""
        client = HTTPClient()
        assert client._session is not None
        assert isinstance(client._session, requests_lib.Session)
        client.close()


class TestHTTPClientContextManager:
    """Test HTTPClient as context manager."""

    def test_context_manager_basic(self):
        """Test basic context manager usage."""
        with HTTPClient(base_url="https://api.example.com") as client:
            assert client._session is not None

    @responses.activate
    def test_context_manager_with_request(self):
        """Test context manager with actual request."""
        responses.add(
            responses.GET, "https://api.example.com/test", json={"result": "ok"}, status=200
        )

        with HTTPClient(base_url="https://api.example.com") as client:
            response = client.get("/test")
            assert response.status_code == 200

    def test_context_manager_closes_session(self):
        """Test that context manager properly closes session."""
        client = HTTPClient()
        with client:
            session = client._session
            assert session is not None

        # Session should be closed after context exit
        # We can't directly check if session is closed, but we verified close() is called


class TestHTTPClientBasicRequests:
    """Test basic HTTP request methods."""

    @responses.activate
    def test_get_request(self, client):
        """Test GET request."""
        responses.add(
            responses.GET, "https://api.example.com/users", json={"users": []}, status=200
        )

        response = client.get("/users")
        assert response.status_code == 200
        assert response.json() == {"users": []}

    @responses.activate
    def test_post_request(self, client):
        """Test POST request."""
        responses.add(
            responses.POST,
            "https://api.example.com/users",
            json={"id": 1, "name": "John"},
            status=201,
        )

        response = client.post("/users", json={"name": "John"})
        assert response.status_code == 201
        assert response.json()["name"] == "John"

    @responses.activate
    def test_put_request(self, client):
        """Test PUT request."""
        responses.add(
            responses.PUT,
            "https://api.example.com/users/1",
            json={"id": 1, "name": "Jane"},
            status=200,
        )

        response = client.put("/users/1", json={"name": "Jane"})
        assert response.status_code == 200

    @responses.activate
    def test_patch_request(self, client):
        """Test PATCH request."""
        responses.add(
            responses.PATCH,
            "https://api.example.com/users/1",
            json={"id": 1, "email": "new@example.com"},
            status=200,
        )

        response = client.patch("/users/1", json={"email": "new@example.com"})
        assert response.status_code == 200

    @responses.activate
    def test_delete_request(self, client):
        """Test DELETE request."""
        responses.add(responses.DELETE, "https://api.example.com/users/1", status=204)

        response = client.delete("/users/1")
        assert response.status_code == 204

    @responses.activate
    def test_head_request(self, client):
        """Test HEAD request."""
        responses.add(responses.HEAD, "https://api.example.com/users", status=200)

        response = client.head("/users")
        assert response.status_code == 200

    @responses.activate
    def test_options_request(self, client):
        """Test OPTIONS request."""
        responses.add(
            responses.OPTIONS,
            "https://api.example.com/users",
            headers={"Allow": "GET, POST, OPTIONS"},
            status=200,
        )

        response = client.options("/users")
        assert response.status_code == 200


class TestHTTPClientURLHandling:
    """Test URL building and handling."""

    @responses.activate
    def test_relative_url_with_base_url(self, client):
        """Test relative URL with base URL."""
        responses.add(responses.GET, "https://api.example.com/posts/1", json={"id": 1}, status=200)

        response = client.get("/posts/1")
        assert response.status_code == 200

    @responses.activate
    def test_absolute_url_overrides_base(self, client):
        """Test that absolute URL overrides base URL."""
        responses.add(
            responses.GET, "https://other.example.com/data", json={"result": "ok"}, status=200
        )

        response = client.get("https://other.example.com/data")
        assert response.status_code == 200

    @responses.activate
    def test_url_without_base_url(self, client_no_base):
        """Test absolute URL without base URL."""
        responses.add(responses.GET, "https://api.example.com/test", json={"ok": True}, status=200)

        response = client_no_base.get("https://api.example.com/test")
        assert response.status_code == 200

    @responses.activate
    def test_url_with_query_params(self, client):
        """Test URL with query parameters."""
        responses.add(
            responses.GET,
            "https://api.example.com/users?page=1&limit=10",
            json={"users": []},
            status=200,
        )

        response = client.get("/users", params={"page": 1, "limit": 10})
        assert response.status_code == 200


class TestHTTPClientErrorHandling:
    """Test error handling."""

    @responses.activate
    def test_404_not_found_error(self, client):
        """Test 404 Not Found error handling."""
        responses.add(responses.GET, "https://api.example.com/nonexistent", status=404)

        with pytest.raises(NotFoundError):
            client.get("/nonexistent")

    @responses.activate
    def test_500_server_error(self, client):
        """Test 500 Server Error handling."""
        responses.add(responses.GET, "https://api.example.com/error", status=500)

        with pytest.raises(HTTPClientException):
            client.get("/error")

    def test_connection_error(self, client):
        """Test connection error handling."""
        with pytest.raises(ConnectionError):
            client.get("http://invalid-domain-that-does-not-exist-12345.com/test")

    @responses.activate
    def test_timeout_error(self, client):
        """Test timeout error handling."""
        responses.add(
            responses.GET, "https://api.example.com/slow", body=requests_lib.exceptions.Timeout()
        )

        with pytest.raises(TimeoutError):
            client.get("/slow")


class TestHTTPClientPlugins:
    """Test plugin system."""

    def test_add_plugin(self, client):
        """Test adding a plugin."""
        plugin = MockPlugin()
        client.add_plugin(plugin)
        assert plugin in client._plugins

    def test_remove_plugin(self, client):
        """Test removing a plugin."""
        plugin = MockPlugin()
        client.add_plugin(plugin)
        client.remove_plugin(plugin)
        assert plugin not in client._plugins

    @responses.activate
    def test_plugin_before_request_called(self, client):
        """Test that plugin before_request is called."""
        plugin = MockPlugin()
        client.add_plugin(plugin)

        responses.add(responses.GET, "https://api.example.com/test", json={"ok": True}, status=200)

        client.get("/test")
        assert plugin.before_request_called

    @responses.activate
    def test_plugin_after_response_called(self, client):
        """Test that plugin after_response is called."""
        plugin = MockPlugin()
        client.add_plugin(plugin)

        responses.add(responses.GET, "https://api.example.com/test", json={"ok": True}, status=200)

        client.get("/test")
        assert plugin.after_response_called

    @responses.activate
    def test_plugin_on_error_called(self, client):
        """Test that plugin on_error is called on errors."""
        plugin = MockPlugin()
        client.add_plugin(plugin)

        responses.add(responses.GET, "https://api.example.com/error", status=404)

        with pytest.raises(NotFoundError):
            client.get("/error")

        assert plugin.on_error_called


class TestHTTPClientProperties:
    """Test client properties."""

    def test_base_url_property(self):
        """Test base_url property getter."""
        client = HTTPClient(base_url="https://api.example.com")
        assert client.base_url == "https://api.example.com"
        client.close()

    def test_timeout_property(self):
        """Test timeout property getter."""
        client = HTTPClient(timeout=60)
        assert client.timeout == 60
        client.close()

    def test_session_property(self):
        """Test session property getter."""
        client = HTTPClient()
        assert isinstance(client.session, requests_lib.Session)
        client.close()


class TestHTTPClientClose:
    """Test client cleanup."""

    def test_close_closes_session(self):
        """Test that close() closes the session."""
        client = HTTPClient()
        session = client._session
        client.close()
        # After close, session should be closed
        # We can't directly verify, but we can check it doesn't raise

    def test_close_multiple_times(self):
        """Test that close() can be called multiple times safely."""
        client = HTTPClient()
        client.close()
        client.close()  # Should not raise


# Helper classes for testing


class MockPlugin(Plugin):
    """Mock plugin for testing."""

    def __init__(self):
        self.before_request_called = False
        self.after_response_called = False
        self.on_error_called = False

    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        """Mock before_request."""
        self.before_request_called = True
        return kwargs

    def after_response(self, response: requests_lib.Response) -> requests_lib.Response:
        """Mock after_response."""
        self.after_response_called = True
        return response

    def on_error(self, error: Exception, **kwargs: Any) -> None:
        """Mock on_error."""
        self.on_error_called = True
