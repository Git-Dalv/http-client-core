"""
Integration tests for HTTPClient logging with real HTTP requests.
"""

import pytest
import responses
import os
import json
import tempfile

from src.http_client.core.http_client import HTTPClient
from src.http_client.core.config import HTTPClientConfig, RetryConfig
from src.http_client.core.logging import LoggingConfig


class TestHTTPClientLoggingIntegration:
    """Integration tests for logging."""

    @responses.activate
    def test_json_logging_to_file(self):
        """Test JSON logging to file with real request."""
        # Mock httpbin.org /get endpoint
        responses.add(
            responses.GET,
            "https://httpbin.org/get",
            json={"args": {}, "headers": {}, "origin": "127.0.0.1", "url": "https://httpbin.org/get"},
            status=200
        )

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
            try:
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
                client.close()

        finally:
            if os.path.exists(log_file):
                os.remove(log_file)

    @responses.activate
    def test_correlation_id_tracking(self):
        """Test correlation ID tracking across requests."""
        # Mock httpbin.org /get endpoint
        responses.add(
            responses.GET,
            "https://httpbin.org/get",
            json={"args": {}, "headers": {"X-Correlation-ID": "test-correlation-123"}, "origin": "127.0.0.1", "url": "https://httpbin.org/get"},
            status=200
        )

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
            try:
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
                client.close()

        finally:
            if os.path.exists(log_file):
                os.remove(log_file)

    def test_retry_logging_integration(self):
        """Test that retries are logged properly."""
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
                backoff_factor=1.0,
                backoff_base=0.1  # Fast retries for testing
            )

            config = HTTPClientConfig(
                base_url="https://httpbin.org",
                logging=logging_config,
                retry=retry_config
            )

            client = HTTPClient(config=config)
            try:
                # This endpoint returns 500, should trigger retries
                try:
                    response = client.get("/status/500")
                except Exception:
                    pass  # Expected to fail

                # Read logs
                with open(log_file, 'r') as f:
                    logs = [json.loads(line) for line in f]

                # Should have multiple retry attempts logged
                retry_logs = [log for log in logs if "retry" in log.get("message", "").lower() or "attempt" in log]
                assert len(retry_logs) > 0
            finally:
                client.close()

        finally:
            if os.path.exists(log_file):
                os.remove(log_file)
