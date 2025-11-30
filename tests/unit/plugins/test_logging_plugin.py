"""
Comprehensive tests for LoggingPlugin - complete coverage.
"""

import pytest
import logging
from unittest.mock import Mock, patch, call
import requests
from src.http_client.plugins.logging_plugin import LoggingPlugin
from src.http_client.core.exceptions import HTTPClientException


class TestLoggingPluginInit:
    """Test LoggingPlugin initialization."""

    def test_plugin_instantiation(self):
        """Test that plugin can be instantiated."""
        plugin = LoggingPlugin()
        assert plugin is not None

    def test_plugin_is_instance_of_plugin_base(self):
        """Test that LoggingPlugin inherits from Plugin."""
        from src.http_client.plugins.plugin import Plugin
        plugin = LoggingPlugin()
        assert isinstance(plugin, Plugin)


class TestLoggingPluginBeforeRequest:
    """Test before_request hook."""

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_before_request_logs_basic_info(self, mock_logger):
        """Test that before_request logs method and URL."""
        plugin = LoggingPlugin()

        result = plugin.before_request("GET", "https://api.example.com/users")

        mock_logger.info.assert_called_once_with(
            "Sending GET request to https://api.example.com/users"
        )
        assert result == {}

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_before_request_logs_post_method(self, mock_logger):
        """Test logging for POST request."""
        plugin = LoggingPlugin()

        plugin.before_request("POST", "https://api.example.com/users")

        mock_logger.info.assert_called_once_with(
            "Sending POST request to https://api.example.com/users"
        )

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_before_request_logs_json_body(self, mock_logger):
        """Test that before_request logs JSON body at debug level."""
        plugin = LoggingPlugin()
        kwargs = {"json": {"name": "John", "email": "john@example.com"}}

        result = plugin.before_request("POST", "https://api.example.com/users", **kwargs)

        mock_logger.info.assert_called_once_with(
            "Sending POST request to https://api.example.com/users"
        )
        mock_logger.debug.assert_called_once_with(
            "Request body: {'name': 'John', 'email': 'john@example.com'}"
        )
        assert result == kwargs

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_before_request_logs_params(self, mock_logger):
        """Test that before_request logs query params at debug level."""
        plugin = LoggingPlugin()
        kwargs = {"params": {"page": 1, "limit": 10}}

        result = plugin.before_request("GET", "https://api.example.com/users", **kwargs)

        mock_logger.info.assert_called_once()
        mock_logger.debug.assert_called_once_with(
            "Request params: {'page': 1, 'limit': 10}"
        )
        assert result == kwargs

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_before_request_logs_both_json_and_params(self, mock_logger):
        """Test logging when both json and params are present."""
        plugin = LoggingPlugin()
        kwargs = {
            "json": {"data": "value"},
            "params": {"filter": "active"}
        }

        result = plugin.before_request("POST", "https://api.example.com/items", **kwargs)

        mock_logger.info.assert_called_once()
        assert mock_logger.debug.call_count == 2
        mock_logger.debug.assert_any_call("Request body: {'data': 'value'}")
        mock_logger.debug.assert_any_call("Request params: {'filter': 'active'}")
        assert result == kwargs

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_before_request_without_json_or_params(self, mock_logger):
        """Test that debug is not called when no json or params."""
        plugin = LoggingPlugin()

        plugin.before_request("GET", "https://api.example.com/status")

        mock_logger.info.assert_called_once()
        mock_logger.debug.assert_not_called()

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_before_request_with_other_kwargs(self, mock_logger):
        """Test before_request with other kwargs like headers, timeout."""
        plugin = LoggingPlugin()
        kwargs = {
            "headers": {"Authorization": "Bearer token"},
            "timeout": 30
        }

        result = plugin.before_request("GET", "https://api.example.com/data", **kwargs)

        # Should only log the basic info, not headers or timeout
        mock_logger.info.assert_called_once()
        mock_logger.debug.assert_not_called()
        assert result == kwargs

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_before_request_preserves_kwargs(self, mock_logger):
        """Test that before_request returns kwargs unchanged."""
        plugin = LoggingPlugin()
        kwargs = {
            "json": {"test": "data"},
            "params": {"key": "value"},
            "headers": {"X-Custom": "header"}
        }

        result = plugin.before_request("POST", "https://api.example.com/test", **kwargs)

        assert result == kwargs

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_before_request_with_complex_json(self, mock_logger):
        """Test logging with complex nested JSON."""
        plugin = LoggingPlugin()
        kwargs = {
            "json": {
                "user": {"name": "John", "age": 30},
                "items": [1, 2, 3],
                "metadata": {"created": "2024-01-01"}
            }
        }

        plugin.before_request("POST", "https://api.example.com/data", **kwargs)

        mock_logger.debug.assert_called_once()
        # Verify the call contains the complex structure
        call_args = mock_logger.debug.call_args[0][0]
        assert "Request body:" in call_args

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_before_request_different_http_methods(self, mock_logger):
        """Test logging for different HTTP methods."""
        plugin = LoggingPlugin()

        methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

        for method in methods:
            mock_logger.reset_mock()
            plugin.before_request(method, "https://api.example.com/test")
            mock_logger.info.assert_called_once_with(
                f"Sending {method} request to https://api.example.com/test"
            )


class TestLoggingPluginAfterResponse:
    """Test after_response hook."""

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_after_response_logs_status_and_url(self, mock_logger):
        """Test that after_response logs status code and URL."""
        plugin = LoggingPlugin()

        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.url = "https://api.example.com/users"
        response.text = "OK"

        result = plugin.after_response(response)

        mock_logger.info.assert_called_once_with(
            "Received response: 200 from https://api.example.com/users"
        )
        assert result == response

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_after_response_logs_response_body_debug(self, mock_logger):
        """Test that after_response logs first 200 chars of response body."""
        plugin = LoggingPlugin()

        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.url = "https://api.example.com/data"
        response.text = '{"result": "success", "data": "test"}'

        plugin.after_response(response)

        mock_logger.debug.assert_called_once_with(
            'Response body: {"result": "success", "data": "test"}...'
        )

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_after_response_truncates_long_body(self, mock_logger):
        """Test that response body is truncated to 200 characters."""
        plugin = LoggingPlugin()

        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.url = "https://api.example.com/data"
        # Create a response longer than 200 chars
        response.text = "x" * 300

        plugin.after_response(response)

        # Should log only first 200 chars
        expected_body = "x" * 200 + "..."
        mock_logger.debug.assert_called_once_with(f"Response body: {expected_body}")

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_after_response_with_201_status(self, mock_logger):
        """Test logging with 201 Created status."""
        plugin = LoggingPlugin()

        response = Mock(spec=requests.Response)
        response.status_code = 201
        response.url = "https://api.example.com/users"
        response.text = '{"id": 1}'

        plugin.after_response(response)

        mock_logger.info.assert_called_once_with(
            "Received response: 201 from https://api.example.com/users"
        )

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_after_response_with_404_status(self, mock_logger):
        """Test logging with 404 Not Found status."""
        plugin = LoggingPlugin()

        response = Mock(spec=requests.Response)
        response.status_code = 404
        response.url = "https://api.example.com/notfound"
        response.text = "Not Found"

        plugin.after_response(response)

        mock_logger.info.assert_called_once_with(
            "Received response: 404 from https://api.example.com/notfound"
        )

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_after_response_with_500_status(self, mock_logger):
        """Test logging with 500 Internal Server Error status."""
        plugin = LoggingPlugin()

        response = Mock(spec=requests.Response)
        response.status_code = 500
        response.url = "https://api.example.com/error"
        response.text = "Internal Server Error"

        plugin.after_response(response)

        mock_logger.info.assert_called_once_with(
            "Received response: 500 from https://api.example.com/error"
        )

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_after_response_preserves_response(self, mock_logger):
        """Test that after_response returns the same response object."""
        plugin = LoggingPlugin()

        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.url = "https://api.example.com/test"
        response.text = "test data"
        response.headers = {"Content-Type": "application/json"}

        result = plugin.after_response(response)

        assert result is response
        assert result.status_code == 200
        assert result.headers == {"Content-Type": "application/json"}

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_after_response_with_empty_body(self, mock_logger):
        """Test logging with empty response body."""
        plugin = LoggingPlugin()

        response = Mock(spec=requests.Response)
        response.status_code = 204
        response.url = "https://api.example.com/delete"
        response.text = ""

        plugin.after_response(response)

        mock_logger.info.assert_called_once()
        mock_logger.debug.assert_called_once_with("Response body: ...")

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_after_response_with_short_body(self, mock_logger):
        """Test logging with body shorter than 200 chars."""
        plugin = LoggingPlugin()

        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.url = "https://api.example.com/data"
        response.text = "Short response"

        plugin.after_response(response)

        mock_logger.debug.assert_called_once_with("Response body: Short response...")

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_after_response_with_json_body(self, mock_logger):
        """Test logging with JSON response body."""
        plugin = LoggingPlugin()

        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.url = "https://api.example.com/users"
        response.text = '{"users": [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]}'

        plugin.after_response(response)

        expected_body = response.text[:200] + "..."
        mock_logger.debug.assert_called_once_with(f"Response body: {expected_body}")


class TestLoggingPluginOnError:
    """Test on_error hook."""

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_on_error_logs_error(self, mock_logger):
        """Test that on_error logs the error message."""
        plugin = LoggingPlugin()
        error = HTTPClientException("Connection timeout")

        plugin.on_error(error)

        mock_logger.error.assert_called_once_with(
            "Request failed with error: Connection timeout"
        )

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_on_error_with_request_exception(self, mock_logger):
        """Test logging with requests.RequestException."""
        plugin = LoggingPlugin()
        error = requests.RequestException("Network error")

        plugin.on_error(error)

        mock_logger.error.assert_called_once_with(
            "Request failed with error: Network error"
        )

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_on_error_with_generic_exception(self, mock_logger):
        """Test logging with generic Exception."""
        plugin = LoggingPlugin()
        error = Exception("Unexpected error")

        plugin.on_error(error)

        mock_logger.error.assert_called_once_with(
            "Request failed with error: Unexpected error"
        )

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_on_error_with_timeout_error(self, mock_logger):
        """Test logging with timeout error."""
        plugin = LoggingPlugin()
        error = requests.Timeout("Request timeout after 30s")

        plugin.on_error(error)

        mock_logger.error.assert_called_once_with(
            "Request failed with error: Request timeout after 30s"
        )

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_on_error_with_connection_error(self, mock_logger):
        """Test logging with connection error."""
        plugin = LoggingPlugin()
        error = requests.ConnectionError("Failed to establish connection")

        plugin.on_error(error)

        mock_logger.error.assert_called_once_with(
            "Request failed with error: Failed to establish connection"
        )

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_on_error_multiple_calls(self, mock_logger):
        """Test multiple error logging calls."""
        plugin = LoggingPlugin()

        plugin.on_error(Exception("Error 1"))
        plugin.on_error(Exception("Error 2"))
        plugin.on_error(Exception("Error 3"))

        assert mock_logger.error.call_count == 3
        mock_logger.error.assert_any_call("Request failed with error: Error 1")
        mock_logger.error.assert_any_call("Request failed with error: Error 2")
        mock_logger.error.assert_any_call("Request failed with error: Error 3")


class TestLoggingPluginIntegration:
    """Test complete request-response-error flow."""

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_complete_successful_request_flow(self, mock_logger):
        """Test logging for complete successful request."""
        plugin = LoggingPlugin()

        # Before request
        kwargs = {"json": {"name": "Test"}}
        plugin.before_request("POST", "https://api.example.com/users", **kwargs)

        # After response
        response = Mock(spec=requests.Response)
        response.status_code = 201
        response.url = "https://api.example.com/users"
        response.text = '{"id": 1, "name": "Test"}'
        plugin.after_response(response)

        # Verify logs
        assert mock_logger.info.call_count == 2
        assert mock_logger.debug.call_count == 2
        mock_logger.error.assert_not_called()

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_complete_failed_request_flow(self, mock_logger):
        """Test logging for failed request."""
        plugin = LoggingPlugin()

        # Before request
        plugin.before_request("GET", "https://api.example.com/data")

        # Error occurs
        error = HTTPClientException("404 Not Found")
        plugin.on_error(error)

        # Verify logs
        mock_logger.info.assert_called_once()
        mock_logger.error.assert_called_once()

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_multiple_requests_logging(self, mock_logger):
        """Test logging for multiple consecutive requests."""
        plugin = LoggingPlugin()

        # First request
        plugin.before_request("GET", "https://api.example.com/users")
        response1 = Mock(spec=requests.Response)
        response1.status_code = 200
        response1.url = "https://api.example.com/users"
        response1.text = "[]"
        plugin.after_response(response1)

        # Second request
        plugin.before_request("POST", "https://api.example.com/users", json={"name": "Test"})
        response2 = Mock(spec=requests.Response)
        response2.status_code = 201
        response2.url = "https://api.example.com/users"
        response2.text = '{"id": 1}'
        plugin.after_response(response2)

        # Should have logged both requests
        assert mock_logger.info.call_count == 4  # 2 before + 2 after


class TestLoggingPluginEdgeCases:
    """Test edge cases and special scenarios."""

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_before_request_with_none_values(self, mock_logger):
        """Test before_request with None values in kwargs."""
        plugin = LoggingPlugin()
        kwargs = {"json": None, "params": None}

        result = plugin.before_request("GET", "https://api.example.com/test", **kwargs)

        # Should not log debug for None values
        mock_logger.info.assert_called_once()
        mock_logger.debug.assert_not_called()

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_after_response_with_unicode_body(self, mock_logger):
        """Test logging with Unicode characters in response."""
        plugin = LoggingPlugin()

        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.url = "https://api.example.com/data"
        response.text = "Тест данных с unicode символами 你好"

        plugin.after_response(response)

        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0][0]
        assert "Тест данных с unicode символами 你好" in call_args

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_on_error_with_empty_error_message(self, mock_logger):
        """Test on_error with exception having empty message."""
        plugin = LoggingPlugin()
        error = Exception("")

        plugin.on_error(error)

        mock_logger.error.assert_called_once_with("Request failed with error: ")

    @patch('src.http_client.plugins.logging_plugin.logger')
    def test_before_request_with_empty_json(self, mock_logger):
        """Test before_request with empty json dict."""
        plugin = LoggingPlugin()
        kwargs = {"json": {}}

        plugin.before_request("POST", "https://api.example.com/test", **kwargs)

        # Empty dict is falsy in Python, so it should not be logged
        mock_logger.debug.assert_not_called()
