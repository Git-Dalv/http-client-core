"""
Tests for HTTPClient.health_check() method.
"""

import pytest
import responses
from src.http_client import HTTPClient
from src.http_client.plugins import LoggingPlugin, CachePlugin


class TestHealthCheckBasic:
    """Basic health_check tests without network."""

    def test_health_check_returns_dict(self):
        """Test that health_check returns a dictionary."""
        client = HTTPClient(base_url="https://api.example.com")

        health = client.health_check()

        assert isinstance(health, dict)
        assert "healthy" in health
        assert "base_url" in health
        assert "plugins_count" in health
        client.close()

    def test_health_check_without_test_url(self):
        """Test health_check without connectivity test."""
        client = HTTPClient(base_url="https://api.example.com")

        health = client.health_check()

        assert health["healthy"] is True
        assert health["base_url"] == "https://api.example.com"
        assert health["connectivity"] is None
        assert health["active_sessions"] >= 0
        client.close()

    def test_health_check_with_plugins(self):
        """Test that plugins are listed in health_check."""
        client = HTTPClient(base_url="https://api.example.com")
        client.add_plugin(LoggingPlugin())
        client.add_plugin(CachePlugin())

        health = client.health_check()

        assert health["plugins_count"] == 2
        assert "LoggingPlugin" in health["plugins"]
        assert "CachePlugin" in health["plugins"]
        client.close()

    def test_health_check_config_info(self):
        """Test that config info is included."""
        client = HTTPClient(
            base_url="https://api.example.com",
            timeout=30,
            max_retries=5,
        )

        health = client.health_check()

        assert "config" in health
        # max_retries=5 translates to max_attempts=6 (5 retries + 1 original attempt)
        assert health["config"]["max_retries"] == 6
        assert health["config"]["verify_ssl"] is True
        client.close()

    def test_health_check_no_base_url(self):
        """Test health_check when no base_url is set."""
        client = HTTPClient()

        health = client.health_check()

        assert health["base_url"] is None
        assert health["healthy"] is True
        client.close()


class TestHealthCheckConnectivity:
    """Health check connectivity tests with mocked responses."""

    @responses.activate
    def test_health_check_reachable(self):
        """Test health_check when URL is reachable."""
        responses.add(
            responses.HEAD,
            "https://api.example.com/health",
            status=200,
        )

        client = HTTPClient(base_url="https://api.example.com")

        health = client.health_check(test_url="https://api.example.com/health")

        assert health["healthy"] is True
        assert health["connectivity"]["reachable"] is True
        assert health["connectivity"]["status_code"] == 200
        assert health["connectivity"]["response_time_ms"] is not None
        assert health["connectivity"]["error"] is None
        client.close()

    @responses.activate
    def test_health_check_server_error(self):
        """Test health_check when server returns 500."""
        responses.add(
            responses.HEAD,
            "https://api.example.com/health",
            status=500,
        )

        client = HTTPClient(base_url="https://api.example.com")

        health = client.health_check(test_url="https://api.example.com/health")

        # Server responded, so it's "reachable" even with 500
        assert health["connectivity"]["reachable"] is True
        assert health["connectivity"]["status_code"] == 500
        client.close()

    @responses.activate
    def test_health_check_connection_error(self):
        """Test health_check when connection fails."""
        responses.add(
            responses.HEAD,
            "https://api.example.com/health",
            body=ConnectionError("Connection refused"),
        )

        client = HTTPClient(base_url="https://api.example.com")

        health = client.health_check(test_url="https://api.example.com/health")

        assert health["healthy"] is False
        assert health["connectivity"]["reachable"] is False
        assert health["connectivity"]["error"] is not None
        assert "Connection" in health["connectivity"]["error"]
        client.close()

    @responses.activate
    def test_health_check_response_time(self):
        """Test that response_time_ms is a non-negative number."""
        responses.add(
            responses.HEAD,
            "https://api.example.com/health",
            status=200,
        )

        client = HTTPClient(base_url="https://api.example.com")

        health = client.health_check(test_url="https://api.example.com/health")

        # With mocked responses, response time can be very fast (close to 0)
        assert health["connectivity"]["response_time_ms"] >= 0
        assert isinstance(health["connectivity"]["response_time_ms"], (int, float))
        assert health["connectivity"]["response_time_ms"] is not None
        client.close()

    @responses.activate
    def test_health_check_custom_timeout(self):
        """Test health_check with custom timeout."""
        responses.add(
            responses.HEAD,
            "https://api.example.com/health",
            status=200,
        )

        client = HTTPClient(base_url="https://api.example.com")

        # Should not raise timeout with custom timeout
        health = client.health_check(
            test_url="https://api.example.com/health",
            timeout=10.0
        )

        assert health["connectivity"]["reachable"] is True
        client.close()


class TestHealthCheckIntegration:
    """Integration-style tests."""

    def test_health_check_after_requests(self):
        """Test health_check reports correct session count after requests."""
        client = HTTPClient(base_url="https://api.example.com")

        # Access session to create it
        _ = client.session

        health = client.health_check()

        assert health["active_sessions"] >= 1
        client.close()

    def test_health_check_structure(self):
        """Test that health_check returns all required fields."""
        client = HTTPClient(base_url="https://api.example.com")

        health = client.health_check()

        # Check all required top-level fields
        required_fields = [
            "healthy",
            "base_url",
            "active_sessions",
            "plugins_count",
            "plugins",
            "config",
            "connectivity",
        ]

        for field in required_fields:
            assert field in health, f"Missing required field: {field}"

        # Check config structure
        config_fields = [
            "timeout_connect",
            "timeout_read",
            "max_retries",
            "verify_ssl",
        ]

        for field in config_fields:
            assert field in health["config"], f"Missing config field: {field}"

        client.close()

    @responses.activate
    def test_health_check_connectivity_structure(self):
        """Test connectivity field structure when test_url is provided."""
        responses.add(
            responses.HEAD,
            "https://api.example.com/health",
            status=200,
        )

        client = HTTPClient(base_url="https://api.example.com")

        health = client.health_check(test_url="https://api.example.com/health")

        # Check connectivity structure
        connectivity_fields = [
            "url",
            "reachable",
            "response_time_ms",
            "status_code",
            "error",
        ]

        assert health["connectivity"] is not None
        for field in connectivity_fields:
            assert field in health["connectivity"], f"Missing connectivity field: {field}"

        client.close()

    def test_health_check_with_context_manager(self):
        """Test health_check works with context manager."""
        with HTTPClient(base_url="https://api.example.com") as client:
            health = client.health_check()

            assert health["healthy"] is True
            assert health["base_url"] == "https://api.example.com"

    def test_health_check_plugins_list_empty(self):
        """Test that plugins list is empty when no plugins added."""
        client = HTTPClient(base_url="https://api.example.com")

        health = client.health_check()

        assert health["plugins_count"] == 0
        assert health["plugins"] == []
        client.close()

    def test_health_check_multiple_calls(self):
        """Test that health_check can be called multiple times."""
        client = HTTPClient(base_url="https://api.example.com")

        health1 = client.health_check()
        health2 = client.health_check()

        assert health1 == health2
        client.close()


class TestHealthCheckEdgeCases:
    """Edge cases and error scenarios."""

    @responses.activate
    def test_health_check_timeout_error(self):
        """Test health_check handles timeout errors."""
        import requests

        # Create a client with very short timeout
        client = HTTPClient(base_url="https://api.example.com")

        # Mock a timeout by not adding any response
        # This will cause a ConnectionError in responses library
        # We'll test timeout differently

        # Actually, let's test with a real timeout scenario
        # by using a non-existent domain that will timeout

        health = client.health_check(
            test_url="http://10.255.255.1:1234",  # Non-routable IP
            timeout=0.1  # Very short timeout
        )

        assert health["healthy"] is False
        assert health["connectivity"]["reachable"] is False
        assert health["connectivity"]["error"] is not None
        client.close()

    def test_health_check_config_values(self):
        """Test that config values are correctly reported."""
        client = HTTPClient(
            base_url="https://api.example.com",
            timeout=45,
            max_retries=10,
            verify_ssl=False,
        )

        health = client.health_check()

        assert health["config"]["timeout_read"] == 45
        # max_retries=10 translates to max_attempts=11 (10 retries + 1 original attempt)
        assert health["config"]["max_retries"] == 11
        assert health["config"]["verify_ssl"] is False
        client.close()

    @responses.activate
    def test_health_check_404_status(self):
        """Test health_check when endpoint returns 404."""
        responses.add(
            responses.HEAD,
            "https://api.example.com/notfound",
            status=404,
        )

        client = HTTPClient(base_url="https://api.example.com")

        health = client.health_check(test_url="https://api.example.com/notfound")

        # 404 means server is reachable, just endpoint not found
        assert health["connectivity"]["reachable"] is True
        assert health["connectivity"]["status_code"] == 404
        client.close()
