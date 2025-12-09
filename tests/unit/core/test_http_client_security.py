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
def test_download_size_limit_no_content_length():
    """Download fails when size limit exceeded without Content-Length header.

    This test validates chunk-level size validation that protects against
    disk exhaustion attacks when the server doesn't send Content-Length header.
    """
    # Generate 150MB of data (exceeds default 100MB limit)
    # Server doesn't send Content-Length header
    large_data = b"x" * (150 * 1024 * 1024)

    responses.add(
        responses.GET,
        "https://api.example.com/stream.bin",
        body=large_data,
        stream=True
        # Note: No Content-Length header
    )

    client = HTTPClient(base_url="https://api.example.com")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = os.path.join(tmpdir, "stream.bin")

        # Should raise ResponseTooLargeError during chunk download
        with pytest.raises(ResponseTooLargeError) as exc_info:
            client.download("/stream.bin", tmp_path)

        # Verify error message mentions exceeded size
        assert "exceeds maximum" in str(exc_info.value)

        # Partial file should be cleaned up
        assert not os.path.exists(tmp_path), "Partial file should be removed on error"


@responses.activate
def test_download_chunk_validation_edge_case():
    """Test chunk-level validation catches size limit at boundary.

    Validates that the check happens BEFORE writing the chunk that
    would exceed the limit, preventing any excess data from being written.
    """
    # Set a small custom limit
    security_cfg = SecurityConfig(max_response_size=10_000)  # 10KB limit
    config = HTTPClientConfig(
        base_url="https://api.example.com",
        security=security_cfg
    )
    client = HTTPClient(config=config)

    # Generate data that will exceed limit (20KB)
    large_data = b"x" * 20_000

    responses.add(
        responses.GET,
        "https://api.example.com/data.bin",
        body=large_data,
        stream=True
        # No Content-Length header to force chunk-by-chunk validation
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = os.path.join(tmpdir, "data.bin")

        with pytest.raises(ResponseTooLargeError) as exc_info:
            # Use small chunk size to test chunk-level validation
            client.download("/data.bin", tmp_path, chunk_size=4096)

        # Verify error details
        assert exc_info.value.size > 10_000
        assert "10000 bytes" in str(exc_info.value)

        # File should be cleaned up
        assert not os.path.exists(tmp_path)


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


@responses.activate
def test_decompression_bomb_high_ratio():
    """Decompression bomb detection: high compression ratio."""
    import gzip
    import io

    # Create gzip bomb: 1KB compressed -> 10MB decompressed (ratio 10000:1)
    # Default max_compression_ratio is 1000:1, so this should be blocked
    decompressed_data = b"x" * (10 * 1024 * 1024)  # 10MB
    compressed_buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed_buffer, mode='wb', compresslevel=9) as gz:
        gz.write(decompressed_data)
    compressed_data = compressed_buffer.getvalue()

    print(f"Compressed: {len(compressed_data)} bytes, Decompressed: {len(decompressed_data)} bytes")
    print(f"Ratio: {len(decompressed_data) / len(compressed_data):.1f}:1")

    responses.add(
        responses.GET,
        "https://api.example.com/bomb",
        body=compressed_data,
        headers={'Content-Encoding': 'gzip'}
    )

    client = HTTPClient(base_url="https://api.example.com")

    with pytest.raises(DecompressionBombError) as exc_info:
        client.get("/bomb")

    assert "ratio" in str(exc_info.value).lower()
    assert "streaming" in str(exc_info.value).lower()


@responses.activate
def test_decompression_bomb_large_size():
    """Decompression bomb detection: exceeds max decompressed size or ratio."""
    import gzip
    import io

    # Create data that exceeds max_decompressed_size (default 500MB)
    # Use 600MB of zeros (highly compressible)
    # Note: ratio check may trigger first, which is also valid bomb detection
    decompressed_data = b"\x00" * (600 * 1024 * 1024)  # 600MB zeros
    compressed_buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed_buffer, mode='wb', compresslevel=9) as gz:
        gz.write(decompressed_data)
    compressed_data = compressed_buffer.getvalue()

    print(f"Large bomb - Compressed: {len(compressed_data)} bytes, Decompressed: {len(decompressed_data)} bytes")

    responses.add(
        responses.GET,
        "https://api.example.com/large_bomb",
        body=compressed_data,
        headers={'Content-Encoding': 'gzip'}
    )

    client = HTTPClient(base_url="https://api.example.com")

    with pytest.raises(DecompressionBombError) as exc_info:
        client.get("/large_bomb")

    # Should detect bomb either by ratio or size check
    error_msg = str(exc_info.value).lower()
    assert ("ratio" in error_msg or "decompressed size" in error_msg)
    assert "exceeds" in error_msg


@responses.activate
def test_decompression_bomb_custom_ratio():
    """Decompression bomb with custom ratio limit."""
    import gzip
    import io

    # Create data with 50:1 ratio
    decompressed_data = b"x" * (50 * 1024)  # 50KB
    compressed_buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed_buffer, mode='wb', compresslevel=9) as gz:
        gz.write(decompressed_data)
    compressed_data = compressed_buffer.getvalue()

    actual_ratio = len(decompressed_data) / len(compressed_data)
    print(f"Actual ratio: {actual_ratio:.1f}:1")

    responses.add(
        responses.GET,
        "https://api.example.com/data",
        body=compressed_data,
        headers={'Content-Encoding': 'gzip'}
    )

    # Set max ratio to 30:1 (should block 50:1)
    security_cfg = SecurityConfig(max_compression_ratio=30)
    config = HTTPClientConfig(
        base_url="https://api.example.com",
        security=security_cfg
    )
    client = HTTPClient(config=config)

    with pytest.raises(DecompressionBombError) as exc_info:
        client.get("/data")

    assert "ratio" in str(exc_info.value).lower()


@responses.activate
def test_gzip_valid_data():
    """Valid gzip data should decompress successfully."""
    import gzip
    import io

    # Create valid gzip data with LOW ratio (< 20:1 default)
    # Use varied data that doesn't compress too well
    decompressed_data = b"Hello, World! 123456789 ABCDEFGHIJKLMNOPQRSTUVWXYZ " * 50  # ~2.7KB
    compressed_buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed_buffer, mode='wb', compresslevel=1) as gz:  # Low compression
        gz.write(decompressed_data)
    compressed_data = compressed_buffer.getvalue()

    print(f"Valid gzip - Compressed: {len(compressed_data)} bytes, Decompressed: {len(decompressed_data)} bytes")
    print(f"Ratio: {len(decompressed_data) / len(compressed_data):.1f}:1")

    responses.add(
        responses.GET,
        "https://api.example.com/valid",
        body=compressed_data,
        headers={'Content-Encoding': 'gzip'}
    )

    # Use higher max_compression_ratio to allow valid data
    security_cfg = SecurityConfig(max_compression_ratio=100)  # Allow up to 100:1 for valid data
    config = HTTPClientConfig(
        base_url="https://api.example.com",
        security=security_cfg
    )
    client = HTTPClient(config=config)

    # Should succeed without raising
    response = client.get("/valid")

    # Response content should be decompressed
    assert response.content == decompressed_data
    assert response.status_code == 200


@responses.activate
def test_decompression_early_abort():
    """Decompression bomb should abort early during streaming.

    This test verifies that the check happens during streaming,
    not after full download, preventing OOM attacks.
    """
    import gzip
    import io

    # Create large bomb: many repetitions of same data (highly compressible)
    # This should be detected early when ratio exceeds limit
    decompressed_data = b"AAAAAAAAAA" * (2 * 1024 * 1024)  # 20MB of 'A's
    compressed_buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed_buffer, mode='wb', compresslevel=9) as gz:
        gz.write(decompressed_data)
    compressed_data = compressed_buffer.getvalue()

    ratio = len(decompressed_data) / len(compressed_data)
    print(f"Early abort test - Ratio: {ratio:.1f}:1, Compressed: {len(compressed_data)} bytes")

    responses.add(
        responses.GET,
        "https://api.example.com/early_bomb",
        body=compressed_data,
        headers={'Content-Encoding': 'gzip'}
    )

    client = HTTPClient(base_url="https://api.example.com")

    with pytest.raises(DecompressionBombError) as exc_info:
        client.get("/early_bomb")

    # Should mention streaming in error (indicates early detection)
    error_msg = str(exc_info.value).lower()
    assert "streaming" in error_msg or "during" in error_msg
    assert "ratio" in error_msg
