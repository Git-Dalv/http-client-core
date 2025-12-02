"""
Unit tests for HTTPClient logging integration.
"""

import pytest
import responses
from unittest.mock import Mock, patch, MagicMock
import time

from src.http_client.core.http_client import HTTPClient
from src.http_client.core.config import HTTPClientConfig
from src.http_client.core.logging import LoggingConfig


class TestHTTPClientLogging:
    """Test logging integration in HTTPClient."""

    @responses.activate
    def test_logging_disabled_by_default(self):
        """Test that logging is disabled when no LoggingConfig provided."""
        responses.add(responses.GET, "https://api.example.com/test", json={"status": "ok"}, status=200)

        config = HTTPClientConfig.create(base_url="https://api.example.com")
        client = HTTPClient(config=config)

        # Logger should be None
        assert client._logger is None

        # Request should work normally
        response = client.get("/test")
        assert response.status_code == 200

    @responses.activate
    def test_logging_enabled_with_config(self):
        """Test that logger is initialized when LoggingConfig provided."""
        responses.add(responses.GET, "https://api.example.com/test", json={"status": "ok"}, status=200)

        logging_config = LoggingConfig.create(level="INFO", format="json", enable_console=False)
        config = HTTPClientConfig.create(
            base_url="https://api.example.com",
            logging=logging_config
        )
        client = HTTPClient(config=config)

        # Logger should be initialized
        assert client._logger is not None
        assert client._logger.name == "http_client.api.example.com"

    @responses.activate
    def test_request_started_logged(self):
        """Test that request started is logged."""
        responses.add(responses.GET, "https://api.example.com/test", json={"status": "ok"}, status=200)

        logging_config = LoggingConfig.create(level="INFO", format="json", enable_console=False)
        config = HTTPClientConfig.create(
            base_url="https://api.example.com",
            logging=logging_config
        )
        client = HTTPClient(config=config)

        # Mock logger
        client._logger.info = Mock()

        response = client.get("/test")

        # Check that info was called with "Request started" and "Request completed"
        calls = client._logger.info.call_args_list
        assert len(calls) >= 2
        assert calls[0][0][0] == "Request started"
        assert calls[-1][0][0] == "Request completed"

    @responses.activate
    def test_request_completed_with_metrics(self):
        """Test that request completed logs include metrics."""
        responses.add(responses.GET, "https://api.example.com/test", json={"status": "ok"}, status=200)

        logging_config = LoggingConfig.create(level="INFO", format="json", enable_console=False)
        config = HTTPClientConfig.create(
            base_url="https://api.example.com",
            logging=logging_config
        )
        client = HTTPClient(config=config)

        # Mock logger
        client._logger.info = Mock()

        response = client.get("/test")

        # Find "Request completed" call
        completed_call = None
        for call in client._logger.info.call_args_list:
            if call[0][0] == "Request completed":
                completed_call = call
                break

        assert completed_call is not None
        kwargs = completed_call[1]
        assert "status_code" in kwargs
        assert kwargs["status_code"] == 200
        assert "duration_ms" in kwargs
        assert "method" in kwargs
        assert "url" in kwargs

    @responses.activate
    def test_request_failed_logged_as_error(self):
        """Test that failed request is logged as error."""
        responses.add(responses.GET, "https://api.example.com/test", status=500)

        from src.http_client.core.config import RetryConfig, TimeoutConfig, ConnectionPoolConfig, SecurityConfig

        logging_config = LoggingConfig.create(level="INFO", format="json", enable_console=False)
        retry_config = RetryConfig(max_attempts=1)  # No retries for this test

        # Use direct construction instead of create() to pass custom retry config
        config = HTTPClientConfig(
            base_url="https://api.example.com",
            timeout=TimeoutConfig(connect=5, read=30),
            retry=retry_config,
            pool=ConnectionPoolConfig(),
            security=SecurityConfig(verify_ssl=True),
            headers={},
            proxies={},
            logging=logging_config
        )
        client = HTTPClient(config=config)

        # Mock logger
        client._logger.error = Mock()

        with pytest.raises(Exception):
            client.get("/test")

        # Error should be logged
        assert client._logger.error.called
        call = client._logger.error.call_args
        assert "Request failed" in call[0][0]
        assert "error" in call[1]

    @responses.activate
    def test_correlation_id_set_and_cleared(self):
        """Test that correlation ID is set and cleared properly."""
        responses.add(responses.GET, "https://api.example.com/test", json={"status": "ok"}, status=200)

        logging_config = LoggingConfig.create(level="INFO", format="json", enable_correlation_id=True)
        config = HTTPClientConfig.create(
            base_url="https://api.example.com",
            logging=logging_config
        )
        client = HTTPClient(config=config)

        with patch('src.http_client.core.logging.filters.set_correlation_id') as mock_set:
            with patch('src.http_client.core.logging.filters.clear_correlation_id') as mock_clear:
                response = client.get("/test")

                # Correlation ID should be set and cleared
                assert mock_set.called
                assert mock_clear.called

    @responses.activate
    def test_retry_attempts_logged(self):
        """Test that retry attempts are logged."""
        # First two calls fail, third succeeds
        responses.add(responses.GET, "https://api.example.com/test", status=500)
        responses.add(responses.GET, "https://api.example.com/test", status=500)
        responses.add(responses.GET, "https://api.example.com/test", json={"status": "ok"}, status=200)

        from src.http_client.core.config import RetryConfig, TimeoutConfig, ConnectionPoolConfig, SecurityConfig

        logging_config = LoggingConfig.create(level="INFO", format="json", enable_console=False)
        retry_config = RetryConfig(max_attempts=3, backoff_factor=1.0)

        # Use direct construction instead of create() to pass custom retry config
        config = HTTPClientConfig(
            base_url="https://api.example.com",
            timeout=TimeoutConfig(connect=5, read=30),
            retry=retry_config,
            pool=ConnectionPoolConfig(),
            security=SecurityConfig(verify_ssl=True),
            headers={},
            proxies={},
            logging=logging_config
        )
        client = HTTPClient(config=config)

        # Mock logger
        client._logger.warning = Mock()

        response = client.get("/test")

        # Should have retry warnings
        assert client._logger.warning.called
        # Should have at least one "Retrying request" call
        retry_calls = [c for c in client._logger.warning.call_args_list if "Retrying" in c[0][0]]
        assert len(retry_calls) >= 1

    @responses.activate
    def test_custom_correlation_id_preserved(self):
        """Test that custom correlation ID from headers is preserved."""
        responses.add(responses.GET, "https://api.example.com/test", json={"status": "ok"}, status=200)

        logging_config = LoggingConfig.create(level="INFO", format="json")
        config = HTTPClientConfig.create(
            base_url="https://api.example.com",
            logging=logging_config
        )
        client = HTTPClient(config=config)

        custom_id = "my-custom-correlation-id"

        with patch('src.http_client.core.logging.filters.set_correlation_id') as mock_set:
            response = client.get("/test", headers={"X-Correlation-ID": custom_id})

            # Should set the custom ID
            mock_set.assert_called_with(custom_id)

    @responses.activate
    def test_logger_name_includes_domain(self):
        """Test that logger name includes domain from base_url."""
        responses.add(responses.GET, "https://api.example.com/test", json={"status": "ok"}, status=200)

        logging_config = LoggingConfig.create(level="INFO", format="json")
        config = HTTPClientConfig.create(
            base_url="https://api.example.com",
            logging=logging_config
        )
        client = HTTPClient(config=config)

        assert "api.example.com" in client._logger.name
