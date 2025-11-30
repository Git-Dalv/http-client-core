"""
Tests for custom exceptions.
"""

import pytest

from src.http_client.core.exceptions import (
    BadRequestError,
    ConnectionError,
    ForbiddenError,
    HTTPClientException,
    NotFoundError,
    ServerError,
    TimeoutError,
    UnauthorizedError,
    HTTPError
)


class TestHTTPClientException:
    """Test base HTTPClientException."""

    def test_exception_message(self):
        """Test exception with message."""
        exc = HTTPClientException("Test error")
        assert str(exc) == "Test error"

    def test_exception_inheritance(self):
        """Test that HTTPClientException inherits from Exception."""
        exc = HTTPClientException("Test")
        assert isinstance(exc, Exception)

    def test_exception_can_be_raised(self):
        """Test that exception can be raised and caught."""
        with pytest.raises(HTTPClientException) as exc_info:
            raise HTTPClientException("Test error")
        assert str(exc_info.value) == "Test error"


class TestConnectionError:
    """Test ConnectionError exception."""

    def test_connection_error_message(self):
        """Test ConnectionError with message."""
        exc = ConnectionError("Connection failed", "https://example.com")
        assert "Connection failed" in str(exc)


    def test_connection_error_with_url(self):
        """Test ConnectionError with URL."""
        exc = ConnectionError("Connection failed", "https://example.com")
        assert "https://example.com" in str(exc)

    def test_connection_error_inheritance(self):
        """Test ConnectionError inherits from HTTPClientException."""
        exc = ConnectionError("Test", "https://example.com")
        assert isinstance(exc, HTTPClientException)


class TestTimeoutError:
    """Test TimeoutError exception."""

    def test_timeout_error_message(self):
        """Test TimeoutError with message."""
        exc = TimeoutError("Request timed out", "https://example.com", 30)
        assert "Request timed out" in str(exc)

    def test_timeout_error_with_url(self):
        """Test TimeoutError with URL."""
        exc = TimeoutError("Timeout", "https://example.com", 30)
        assert "example.com" in str(exc)


    def test_timeout_error_with_timeout_value(self):
        """Test TimeoutError with timeout value."""
        exc = TimeoutError("Timeout", "https://example.com", 30)
        message = str(exc)
        assert "https://example.com" in message
        assert "30" in message


class TestNotFoundError:
    """Test NotFoundError exception."""

    def test_not_found_error_message(self):
        """Test NotFoundError with message."""
        exc = NotFoundError("https://example.com", "Resource not found")
        assert "Resource not found" in str(exc)
        assert "404" in str(exc)

    def test_not_found_error_inheritance(self):
        """Test NotFoundError inherits from HTTPClientException."""
        exc = NotFoundError("Test")
        assert isinstance(exc, HTTPClientException)


class TestBadRequestError:
    """Test BadRequestError exception."""

    def test_bad_request_error_message(self):
        """Test BadRequestError with message."""
        exc = BadRequestError("Invalid request")
        assert isinstance(exc, BadRequestError)

    def test_bad_request_error_inheritance(self):
        """Test BadRequestError inherits from HTTPClientException."""
        exc = BadRequestError("Test")
        assert isinstance(exc, HTTPClientException)


class TestUnauthorizedError:
    """Test UnauthorizedError exception."""

    def test_unauthorized_error_message(self):
        """Test UnauthorizedError with message."""
        exc = UnauthorizedError("Unauthorized")
        assert isinstance(exc, UnauthorizedError)

    def test_unauthorized_error_inheritance(self):
        """Test UnauthorizedError inherits from HTTPClientException."""
        exc = UnauthorizedError("Test")
        assert isinstance(exc, HTTPClientException)


class TestForbiddenError:
    """Test ForbiddenError exception."""

    def test_forbidden_error_message(self):
        """Test ForbiddenError with message."""
        exc = ForbiddenError("Forbidden")
        assert isinstance(exc, ForbiddenError)

    def test_forbidden_error_inheritance(self):
        """Test ForbiddenError inherits from HTTPClientException."""
        exc = ForbiddenError("Test")
        assert isinstance(exc, HTTPClientException)


class TestServerError:
    """Test ServerError exception."""

    def test_server_error_message(self):
        """Test ServerError with message."""
        exc = ServerError(500, "https://example.com", "Server error")
        assert isinstance(exc, ServerError)

    def test_server_error_inheritance(self):
        """Test ServerError inherits from HTTPClientException."""
        exc = ServerError(500, "https://example.com", "Test")
        assert isinstance(exc, HTTPError)
