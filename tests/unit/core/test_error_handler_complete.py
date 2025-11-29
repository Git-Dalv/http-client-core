"""
Comprehensive tests for ErrorHandler.
"""

import pytest
from unittest.mock import Mock
import requests
from src.http_client.core.error_handler import ErrorHandler
from src.http_client.core.exceptions import (
    ConnectionError,
    TimeoutError,
    NotFoundError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    ServerError,
    HTTPClientException
)


class TestErrorHandler:
    """Test ErrorHandler class."""

    def test_init(self):
        """Test ErrorHandler initialization."""
        handler = ErrorHandler()
        assert handler is not None

    def test_handle_404_error(self):
        """Test handling 404 error."""
        handler = ErrorHandler()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        error = requests.exceptions.HTTPError(response=mock_response)
        error.response = mock_response

        with pytest.raises(NotFoundError) as exc_info:
            handler.handle_request_exception(error, "https://example.com/test", 30)

        assert "404" in str(exc_info.value) or "Not Found" in str(exc_info.value)

    def test_handle_400_error(self):
        """Test handling 400 error."""
        handler = ErrorHandler()
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        error = requests.exceptions.HTTPError(response=mock_response)
        error.response = mock_response

        with pytest.raises(BadRequestError):
            handler.handle_request_exception(error, "https://example.com/test", 30)

    def test_handle_401_error(self):
        """Test handling 401 error."""
        handler = ErrorHandler()
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        error = requests.exceptions.HTTPError(response=mock_response)
        error.response = mock_response

        with pytest.raises(UnauthorizedError):
            handler.handle_request_exception(error, "https://example.com/test", 30)

    def test_handle_403_error(self):
        """Test handling 403 error."""
        handler = ErrorHandler()
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        error = requests.exceptions.HTTPError(response=mock_response)
        error.response = mock_response

        with pytest.raises(ForbiddenError):
            handler.handle_request_exception(error, "https://example.com/test", 30)

    def test_handle_500_error(self):
        """Test handling 500 error."""
        handler = ErrorHandler()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        error = requests.exceptions.HTTPError(response=mock_response)
        error.response = mock_response

        with pytest.raises(ServerError):
            handler.handle_request_exception(error, "https://example.com/test", 30)

    def test_handle_timeout_error(self):
        """Test handling timeout error."""
        handler = ErrorHandler()
        error = requests.exceptions.Timeout("Request timed out")

        with pytest.raises(TimeoutError) as exc_info:
            handler.handle_request_exception(error, "https://example.com/test", 30)

        assert "30" in str(exc_info.value)

    def test_handle_connection_error(self):
        """Test handling connection error."""
        handler = ErrorHandler()
        error = requests.exceptions.ConnectionError("Connection failed")

        with pytest.raises(ConnectionError) as exc_info:
            handler.handle_request_exception(error, "https://example.com/test", 30)

        assert "https://example.com/test" in str(exc_info.value)

    def test_handle_generic_request_exception(self):
        """Test handling generic RequestException."""
        handler = ErrorHandler()
        error = requests.exceptions.RequestException("Generic error")

        with pytest.raises(HTTPClientException):
            handler.handle_request_exception(error, "https://example.com/test", 30)

    def test_handle_http_error_without_response(self):
        """Test handling HTTPError without response attribute."""
        handler = ErrorHandler()
        error = requests.exceptions.HTTPError("HTTP Error")
        # Don't set error.response

        with pytest.raises(HTTPClientException):
            handler.handle_request_exception(error, "https://example.com/test", 30)
