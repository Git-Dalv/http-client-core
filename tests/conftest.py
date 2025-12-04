"""
Pytest configuration and fixtures for http-client-core tests.
"""

import pytest
import responses as responses_lib

from src.http_client.core.http_client import HTTPClient
from src.http_client.core.logging.config import LoggingConfig


@pytest.fixture
def base_url():
    """Base URL for testing."""
    return "https://api.example.com"


@pytest.fixture
def mock_responses():
    """Mock HTTP responses using responses library."""
    with responses_lib.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def client(base_url):
    """HTTP client instance for testing."""
    client = HTTPClient(base_url=base_url, timeout=10)
    yield client
    client.close()


@pytest.fixture
def client_no_base():
    """HTTP client without base URL."""
    client = HTTPClient(timeout=10)
    yield client
    client.close()


@pytest.fixture
def logging_config():
    """
    LoggingConfig fixture for testing.

    Provides a standard logging configuration to use instead of deprecated
    LoggingPlugin. Use this in tests that need logging configuration.

    Example:
        def test_with_logging(logging_config):
            config = HTTPClientConfig.create(logging=logging_config)
            client = HTTPClient(config=config)
    """
    return LoggingConfig.create(
        level="DEBUG",
        enable_console=True,
        enable_file=False
    )


@pytest.fixture
def logging_config_with_file(tmp_path):
    """
    LoggingConfig fixture with file logging enabled.

    Uses temporary directory for log files to avoid cleanup issues.
    """
    log_file = tmp_path / "test.log"
    return LoggingConfig.create(
        level="DEBUG",
        enable_console=False,
        enable_file=True,
        file_path=str(log_file)
    )
