"""Тесты security features HTTPClient."""

import pytest
import responses
import tempfile
import os
from src.http_client import HTTPClient
from src.http_client.core.config import HTTPClientConfig, SecurityConfig
from src.http_client.core.exceptions import ResponseTooLargeError, DecompressionBombError


@responses.activate
def test_response_size_limit_content_length():
    """Response size limit через Content-Length header."""
    # Response claims to be 200MB - generate actual 200MB to match Content-Length
    large_data = b"x" * (200 * 1024 * 1024)

    responses.add(
        responses.GET,
        "https://api.example.com/large",
        headers={'Content-Length': str(len(large_data))},
        body=large_data
    )

    config = HTTPClientConfig.create(
        base_url="https://api.example.com"
    )
    # max_response_size по умолчанию 100MB
    client = HTTPClient(config=config)

    with pytest.raises(ResponseTooLargeError) as exc_info:
        client.get("/large")

    assert "exceeds maximum" in str(exc_info.value)


@responses.activate
def test_response_size_limit_actual_content():
    """Response size limit через actual content."""
    # Generate 150MB of data
    large_data = b"x" * (150 * 1024 * 1024)

    responses.add(
        responses.GET,
        "https://api.example.com/large",
        body=large_data
    )

    client = HTTPClient(base_url="https://api.example.com")

    with pytest.raises(ResponseTooLargeError):
        client.get("/large")


@responses.activate
def test_response_size_custom_limit():
    """Custom response size limit."""
    responses.add(
        responses.GET,
        "https://api.example.com/data",
        body=b"x" * 1024  # 1KB
    )

    # Set limit to 512 bytes
    security_cfg = SecurityConfig(max_response_size=512)
    config = HTTPClientConfig(
        base_url="https://api.example.com",
        security=security_cfg
    )
    client = HTTPClient(config=config)

    with pytest.raises(ResponseTooLargeError):
        client.get("/data")


@responses.activate
def test_download_success():
    """Download file successfully."""
    data = b"Hello, World!" * 1000

    responses.add(
        responses.GET,
        "https://api.example.com/file.txt",
        body=data,
        headers={'Content-Length': str(len(data))}
    )

    client = HTTPClient(base_url="https://api.example.com")

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name

    try:
        bytes_downloaded = client.download("/file.txt", tmp_path)

        assert bytes_downloaded == len(data)
        assert os.path.exists(tmp_path)

        with open(tmp_path, 'rb') as f:
            assert f.read() == data
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@responses.activate
def test_download_size_limit():
    """Download fails if file too large."""
    responses.add(
        responses.GET,
        "https://api.example.com/huge.bin",
        headers={'Content-Length': str(200 * 1024 * 1024)},  # 200MB
        body=b"fake data"
    )

    client = HTTPClient(base_url="https://api.example.com")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = os.path.join(tmpdir, "huge.bin")

        with pytest.raises(ResponseTooLargeError):
            client.download("/huge.bin", tmp_path)

        # File should not exist or be cleaned up
        # (may not be created if Content-Length check fails before download starts)
        # This is OK either way


@responses.activate
def test_correlation_id_added():
    """Correlation ID добавляется автоматически."""
    responses.add(responses.GET, "https://api.example.com/test", json={"ok": True})

    client = HTTPClient(base_url="https://api.example.com")
    response = client.get("/test")

    # Check request had correlation ID
    request_headers = responses.calls[0].request.headers
    assert 'X-Correlation-ID' in request_headers

    # Should be valid UUID format
    correlation_id = request_headers['X-Correlation-ID']
    assert len(correlation_id) == 36  # UUID string length
    assert correlation_id.count('-') == 4  # UUID has 4 dashes


@responses.activate
def test_correlation_id_preserved():
    """Correlation ID не переписывается если уже есть."""
    responses.add(responses.GET, "https://api.example.com/test", json={"ok": True})

    custom_id = "my-custom-correlation-id"
    client = HTTPClient(base_url="https://api.example.com")
    response = client.get("/test", headers={'X-Correlation-ID': custom_id})

    # Should preserve custom ID
    request_headers = responses.calls[0].request.headers
    assert request_headers['X-Correlation-ID'] == custom_id
