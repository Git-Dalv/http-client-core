"""Тесты для новой иерархии исключений."""

import pytest
from src.http_client.core.exceptions import *

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Базовая классификация
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_temporary_error_is_retryable():
    """Временные ошибки retryable."""
    exc = TemporaryError("test")
    assert exc.retryable is True
    assert exc.fatal is False

def test_fatal_error_is_not_retryable():
    """Фатальные ошибки не retryable."""
    exc = FatalError("test")
    assert exc.fatal is True
    assert exc.retryable is False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Network errors (временные)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_timeout_error():
    """Тест TimeoutError."""
    exc = TimeoutError(
        "Timeout",
        "https://example.com",
        timeout=30,
        timeout_type="read"
    )
    assert exc.retryable is True
    assert exc.url == "https://example.com"
    assert exc.timeout == 30
    assert "read timeout" in str(exc)

def test_connection_error():
    """Тест ConnectionError."""
    exc = ConnectionError("Failed", "https://example.com")
    assert exc.retryable is True
    assert exc.url == "https://example.com"

def test_proxy_error():
    """Тест ProxyError."""
    exc = ProxyError(
        "Proxy failed",
        "https://example.com",
        proxy="http://proxy:8080"
    )
    assert exc.retryable is True
    assert "proxy:8080" in str(exc)

def test_server_error():
    """Тест ServerError (5xx)."""
    exc = ServerError(500, "https://example.com", "Internal error")
    assert exc.retryable is True
    assert exc.status_code == 500
    assert "500" in str(exc)

def test_too_many_requests_error():
    """Тест TooManyRequestsError (429)."""
    exc = TooManyRequestsError(
        "https://example.com",
        retry_after=60
    )
    assert exc.retryable is True
    assert exc.retry_after == 60
    assert "60s" in str(exc)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Client errors (фатальные)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_bad_request_error():
    """Тест BadRequestError (400)."""
    exc = BadRequestError("https://example.com", "Invalid data")
    assert exc.fatal is True
    assert exc.status_code == 400

def test_unauthorized_error():
    """Тест UnauthorizedError (401)."""
    exc = UnauthorizedError("https://example.com")
    assert exc.fatal is True
    assert exc.status_code == 401

def test_forbidden_error():
    """Тест ForbiddenError (403)."""
    exc = ForbiddenError("https://example.com")
    assert exc.fatal is True
    assert exc.status_code == 403

def test_not_found_error():
    """Тест NotFoundError (404)."""
    exc = NotFoundError("https://example.com")
    assert exc.fatal is True
    assert exc.status_code == 404

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Response errors
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_response_too_large_error():
    """Тест ResponseTooLargeError."""
    exc = ResponseTooLargeError(
        "Response size (200000000 bytes) exceeds maximum (100000000 bytes)",
        url="https://example.com",
        size=200_000_000,
        max_size=100_000_000
    )
    assert exc.fatal is True
    assert exc.size == 200_000_000
    assert "200000000 bytes" in str(exc)

def test_decompression_bomb_error():
    """Тест DecompressionBombError."""
    exc = DecompressionBombError(
        "Decompression bomb detected: 1000 -> 1000000 bytes (ratio: 1000.0:1)",
        url="https://example.com",
        compressed_size=1000,
        decompressed_size=1_000_000
    )
    assert exc.fatal is True
    assert "1000" in str(exc)

def test_too_many_retries_error():
    """Тест TooManyRetriesError."""
    last_exc = TimeoutError("Timeout", "https://example.com")
    exc = TooManyRetriesError(
        max_retries=3,
        last_error=last_exc,
        url="https://example.com"
    )
    assert "Max retries (3)" in str(exc)
    assert "Timeout" in str(exc)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# classify_requests_exception
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_classify_timeout():
    """Тест классификации Timeout."""
    import requests
    req_exc = requests.exceptions.Timeout()
    our_exc = classify_requests_exception(req_exc, "https://example.com")

    assert isinstance(our_exc, TimeoutError)
    assert our_exc.retryable is True

def test_classify_connection_error():
    """Тест классификации ConnectionError."""
    import requests
    req_exc = requests.exceptions.ConnectionError()
    our_exc = classify_requests_exception(req_exc, "https://example.com")

    assert isinstance(our_exc, ConnectionError)
    assert our_exc.retryable is True

def test_classify_http_error_404():
    """Тест классификации HTTPError 404."""
    import requests
    from unittest.mock import Mock

    response = Mock()
    response.status_code = 404

    req_exc = requests.exceptions.HTTPError()
    req_exc.response = response

    our_exc = classify_requests_exception(req_exc, "https://example.com")

    assert isinstance(our_exc, NotFoundError)
    assert our_exc.fatal is True

def test_classify_http_error_500():
    """Тест классификации HTTPError 500."""
    import requests
    from unittest.mock import Mock

    response = Mock()
    response.status_code = 500

    req_exc = requests.exceptions.HTTPError()
    req_exc.response = response

    our_exc = classify_requests_exception(req_exc, "https://example.com")

    assert isinstance(our_exc, ServerError)
    assert our_exc.retryable is True
