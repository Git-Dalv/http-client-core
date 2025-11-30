"""
Pytest configuration and fixtures for http-client-core tests.
"""

import pytest
import responses as responses_lib

from src.http_client.core.http_client import HTTPClient


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
