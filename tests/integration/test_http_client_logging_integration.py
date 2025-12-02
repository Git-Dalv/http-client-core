"""
Integration tests for HTTPClient logging with real HTTP requests.
"""

import pytest
import os
import json
import tempfile
import responses

from src.http_client.core.http_client import HTTPClient
from src.http_client.core.config import HTTPClientConfig, RetryConfig, TimeoutConfig, ConnectionPoolConfig, SecurityConfig
from src.http_client.core.logging import LoggingConfig


class TestHTTPClientLoggingIntegration:
    """Integration tests for logging."""

    @responses.activate
    def test_json_logging_to_file(self):
        """Test JSON logging to file with mocked request."""
        # Mock the HTTP request
        responses.add(responses.GET, "https://httpbin.org/get", json={"status": "ok"}, status=200)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name

        try:
            logging_config = LoggingConfig.create(
                level="INFO",
                format="json",
                enable_console=False,
                enable_file=True,
                file_path=log_file
            )

            config = HTTPClientConfig.create(
                base_url="https://httpbin.org",
                logging=logging_config
            )

            client = HTTPClient(config=config)
            response = client.get("/get")

            assert response.status_code == 200

            # Read log file
            with open(log_file, 'r') as f:
                logs = [json.loads(line) for line in f]

            # Should have at least 2 logs (started + completed)
            assert len(logs) >= 2

            # Check first log (started)
            started_log = logs[0]
            assert started_log["message"] == "Request started"
            assert started_log["method"] == "GET"
            assert "https://httpbin.org/get" in started_log["url"]

            # Check last log (completed)
            completed_log = logs[-1]
            assert completed_log["message"] == "Request completed"
            assert completed_log["status_code"] == 200
            assert "duration_ms" in completed_log

        finally:
            if os.path.exists(log_file):
                os.remove(log_file)

    @responses.activate
    def test_correlation_id_tracking(self):
        """Test correlation ID tracking across requests."""
        # Mock the HTTP request
        responses.add(responses.GET, "https://httpbin.org/get", json={"status": "ok"}, status=200)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name

        try:
            logging_config = LoggingConfig.create(
                level="INFO",
                format="json",
                enable_console=False,
                enable_file=True,
                file_path=log_file,
                enable_correlation_id=True
            )

            config = HTTPClientConfig.create(
                base_url="https://httpbin.org",
                logging=logging_config
            )

            client = HTTPClient(config=config)

            # Make request with custom correlation ID
            custom_id = "test-correlation-123"
            response = client.get("/get", headers={"X-Correlation-ID": custom_id})

            # Read logs
            with open(log_file, 'r') as f:
                logs = [json.loads(line) for line in f]

            # All logs should have the same correlation ID
            for log in logs:
                assert log.get("correlation_id") == custom_id

        finally:
            if os.path.exists(log_file):
                os.remove(log_file)

    @responses.activate
    def test_retry_logging_integration(self):
        """Test that retries are logged properly."""
        # Mock HTTP requests: first two fail, third succeeds
        responses.add(responses.GET, "https://httpbin.org/status/500", status=500)
        responses.add(responses.GET, "https://httpbin.org/status/500", status=500)
        responses.add(responses.GET, "https://httpbin.org/status/500", json={"status": "ok"}, status=200)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name

        try:
            logging_config = LoggingConfig.create(
                level="INFO",
                format="json",
                enable_console=False,
                enable_file=True,
                file_path=log_file
            )

            retry_config = RetryConfig(
                max_attempts=3,
                backoff_factor=1.0  # Fast retries for testing
            )

            # Use direct construction to pass custom retry config
            config = HTTPClientConfig(
                base_url="https://httpbin.org",
                timeout=TimeoutConfig(connect=5, read=30),
                retry=retry_config,
                pool=ConnectionPoolConfig(),
                security=SecurityConfig(verify_ssl=True),
                headers={},
                proxies={},
                logging=logging_config
            )

            client = HTTPClient(config=config)

            # This endpoint returns 500 twice then 200, should trigger retries
            response = client.get("/status/500")
            assert response.status_code == 200

            # Read logs
            with open(log_file, 'r') as f:
                logs = [json.loads(line) for line in f]

            # Should have multiple retry attempts logged
            retry_logs = [log for log in logs if "retry" in log.get("message", "").lower() or "attempt" in log]
            assert len(retry_logs) > 0

        finally:
            if os.path.exists(log_file):
                os.remove(log_file)
