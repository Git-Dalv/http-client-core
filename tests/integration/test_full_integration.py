"""
Интеграционные тесты для проверки работы всех компонентов вместе.
"""

import pytest
import responses

from src.http_client.core.exceptions import HTTPClientException
from src.http_client.core.http_client import HTTPClient
from src.http_client.plugins.logging_plugin import LoggingPlugin
from src.http_client.plugins.monitoring_plugin import MonitoringPlugin
from src.http_client.plugins.retry_plugin import RetryPlugin


@pytest.mark.integration
class TestFullIntegration:
    """Тесты всей системы работающей вместе."""

    @responses.activate
    def test_client_with_all_plugins(self):
        """Test HTTPClient with all plugins enabled."""
        monitoring = MonitoringPlugin()
        retry = RetryPlugin(max_retries=3)
        logging = LoggingPlugin()

        client = HTTPClient(base_url="https://api.example.com", timeout=10)
        client.add_plugin(monitoring)
        client.add_plugin(retry)
        client.add_plugin(logging)

        responses.add(
            responses.GET, "https://api.example.com/users", json={"users": []}, status=200
        )

        response = client.get("/users")

        assert response.status_code == 200
        # Проверяем что монitorинг сработал
        metrics = monitoring.get_metrics()
        assert metrics["total_requests"] >= 1

        client.close()

    @responses.activate
    def test_retry_with_monitoring(self):
        """Test that retry plugin works with monitoring."""
        monitoring = MonitoringPlugin()
        retry = RetryPlugin(max_retries=5, backoff_factor=0.1)

        client = HTTPClient(base_url="https://api.example.com", timeout=10)
        client.add_plugin(monitoring)
        client.add_plugin(retry)

        # First call fails, second succeeds
        responses.add(responses.GET, "https://api.example.com/data", status=500)
        responses.add(responses.GET, "https://api.example.com/data", status=500)
        responses.add(responses.GET, "https://api.example.com/data", status=500)
        responses.add(responses.GET, "https://api.example.com/data", status=200)
        responses.add(responses.GET, "https://api.example.com/data", json={"ok": True}, status=200)

        response = client.get("/data")

        assert response.status_code == 200
        # Проверяем метрики: должно быть 2 запроса (1 fail + 1 success)
        metrics = monitoring.get_metrics()
        assert metrics["total_requests"] >= 1

        client.close()

    @responses.activate
    def test_multiple_requests_with_monitoring(self):
        """Test multiple requests with monitoring plugin."""
        monitoring = MonitoringPlugin()
        client = HTTPClient(base_url="https://api.example.com", timeout=10)
        client.add_plugin(monitoring)

        # Setup responses
        responses.add(
            responses.GET, "https://api.example.com/users", json={"users": []}, status=200
        )
        responses.add(responses.POST, "https://api.example.com/users", json={"id": 1}, status=201)
        responses.add(
            responses.GET, "https://api.example.com/posts", json={"posts": []}, status=200
        )

        # Make requests
        client.get("/users")
        client.post("/users", json={"name": "Test"})
        client.get("/posts")

        # Check metrics
        metrics = monitoring.get_metrics()
        assert metrics["total_requests"] == 3
        assert "GET" in metrics["method_stats"]
        assert "POST" in metrics["method_stats"]

        client.close()

    @responses.activate
    def test_error_handling_with_all_plugins(self):
        """Test error handling with all plugins enabled."""
        monitoring = MonitoringPlugin(track_errors=True)
        retry = RetryPlugin(max_retries=3, backoff_factor=0.1)
        logging = LoggingPlugin()

        client = HTTPClient(base_url="https://api.example.com", timeout=10)
        client.add_plugin(monitoring)
        client.add_plugin(retry)
        client.add_plugin(logging)

        # All requests fail
        responses.add(responses.GET, "https://api.example.com/error", status=404)
        responses.add(responses.GET, "https://api.example.com/error", status=404)

        with pytest.raises(HTTPClientException):
            client.get("/error")

        # Check that error was tracked
        errors = monitoring.get_recent_errors()
        assert len(errors) >= 1

        client.close()

    @responses.activate
    def test_context_manager_with_plugins(self):
        """Test context manager usage with plugins."""
        monitoring = MonitoringPlugin()

        responses.add(responses.GET, "https://api.example.com/test", json={"ok": True}, status=200)

        with HTTPClient(base_url="https://api.example.com", timeout=10) as client:
            client.add_plugin(monitoring)
            response = client.get("/test")
            assert response.status_code == 200

        # After context exit, metrics should still be accessible
        metrics = monitoring.get_metrics()
        assert metrics["total_requests"] == 1


@pytest.mark.integration
class TestPluginInteractions:
    """Test interactions between different plugins."""

    @responses.activate
    def test_monitoring_tracks_retries(self):
        """Test that monitoring correctly tracks retry attempts."""
        monitoring = MonitoringPlugin()
        retry = RetryPlugin(max_retries=5, backoff_factor=0.1)

        client = HTTPClient(base_url="https://api.example.com", timeout=10)
        client.add_plugin(retry)
        client.add_plugin(monitoring)

        # Setup multiple failures then success
        responses.add(responses.GET, "https://api.example.com/flaky", status=500)
        responses.add(responses.GET, "https://api.example.com/flaky", status=500)
        responses.add(responses.GET, "https://api.example.com/flaky", status=500)
        responses.add(responses.GET, "https://api.example.com/flaky", json={"ok": True}, status=200)

        response = client.get("/flaky")
        assert response.status_code == 200

        client.close()

    @responses.activate
    def test_logging_with_monitoring(self):
        """Test that logging and monitoring work together."""
        monitoring = MonitoringPlugin()
        logging = LoggingPlugin()

        client = HTTPClient(base_url="https://api.example.com", timeout=10)
        client.add_plugin(logging)
        client.add_plugin(monitoring)

        responses.add(
            responses.GET, "https://api.example.com/data", json={"result": "ok"}, status=200
        )

        response = client.get("/data")
        assert response.status_code == 200

        # Check monitoring metrics
        metrics = monitoring.get_metrics()
        assert metrics["total_requests"] == 1

        client.close()


@pytest.mark.integration
class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    @responses.activate
    def test_api_client_workflow(self):
        """Test typical API client workflow."""
        monitoring = MonitoringPlugin()
        client = HTTPClient(base_url="https://api.example.com", timeout=10)
        client.add_plugin(monitoring)

        # Setup responses for typical workflow
        responses.add(
            responses.GET, "https://api.example.com/users", json={"users": [{"id": 1}]}, status=200
        )
        responses.add(
            responses.GET,
            "https://api.example.com/users/1",
            json={"id": 1, "name": "Test"},
            status=200,
        )
        responses.add(
            responses.PUT,
            "https://api.example.com/users/1",
            json={"id": 1, "name": "Updated"},
            status=200,
        )
        responses.add(responses.DELETE, "https://api.example.com/users/1", status=204)

        # Execute workflow
        users = client.get("/users")
        assert users.status_code == 200

        user = client.get("/users/1")
        assert user.status_code == 200

        updated = client.put("/users/1", json={"name": "Updated"})
        assert updated.status_code == 200

        deleted = client.delete("/users/1")
        assert deleted.status_code == 204

        # Verify metrics
        metrics = monitoring.get_metrics()
        assert metrics["total_requests"] == 4
        assert metrics["failed_requests"] == 0

        client.close()
