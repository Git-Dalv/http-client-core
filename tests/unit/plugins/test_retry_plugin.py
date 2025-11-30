"""
Comprehensive tests for RetryPlugin - complete coverage.
"""

from unittest.mock import Mock, patch

import requests

from src.http_client.core.exceptions import HTTPClientException
from src.http_client.plugins.retry_plugin import RetryPlugin


class TestRetryPluginInit:
    """Test RetryPlugin initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        plugin = RetryPlugin()
        assert plugin.max_retries == 3
        assert plugin.backoff_factor == 0.5
        assert plugin.retry_count == 0

    def test_init_with_custom_max_retries(self):
        """Test initialization with custom max_retries."""
        plugin = RetryPlugin(max_retries=5)
        assert plugin.max_retries == 5
        assert plugin.backoff_factor == 0.5

    def test_init_with_custom_backoff_factor(self):
        """Test initialization with custom backoff_factor."""
        plugin = RetryPlugin(backoff_factor=1.0)
        assert plugin.max_retries == 3
        assert plugin.backoff_factor == 1.0

    def test_init_with_all_custom_params(self):
        """Test initialization with all custom parameters."""
        plugin = RetryPlugin(max_retries=10, backoff_factor=2.0)
        assert plugin.max_retries == 10
        assert plugin.backoff_factor == 2.0
        assert plugin.retry_count == 0

    def test_init_with_zero_retries(self):
        """Test initialization with zero retries."""
        plugin = RetryPlugin(max_retries=0)
        assert plugin.max_retries == 0

    def test_init_with_zero_backoff(self):
        """Test initialization with zero backoff factor."""
        plugin = RetryPlugin(backoff_factor=0.0)
        assert plugin.backoff_factor == 0.0


class TestRetryPluginBeforeRequest:
    """Test before_request hook."""

    def test_before_request_saves_params(self):
        """Test that before_request saves request parameters."""
        plugin = RetryPlugin()
        kwargs = {"headers": {"X-Test": "value"}, "timeout": 30}

        result = plugin.before_request("GET", "https://api.example.com/test", **kwargs)

        assert result == kwargs
        assert plugin.last_request == {
            "method": "GET",
            "url": "https://api.example.com/test",
            "kwargs": kwargs,
        }

    def test_before_request_with_empty_kwargs(self):
        """Test before_request with empty kwargs."""
        plugin = RetryPlugin()

        result = plugin.before_request("POST", "https://api.example.com/data")

        assert result == {}
        assert plugin.last_request["method"] == "POST"
        assert plugin.last_request["url"] == "https://api.example.com/data"
        assert plugin.last_request["kwargs"] == {}

    def test_before_request_with_json_data(self):
        """Test before_request with JSON data."""
        plugin = RetryPlugin()
        kwargs = {"json": {"name": "test"}, "headers": {"Content-Type": "application/json"}}

        result = plugin.before_request("POST", "https://api.example.com/users", **kwargs)

        assert result == kwargs
        assert plugin.last_request["kwargs"]["json"] == {"name": "test"}

    def test_before_request_overwrites_previous(self):
        """Test that before_request overwrites previous saved request."""
        plugin = RetryPlugin()

        plugin.before_request("GET", "https://api.example.com/first")
        plugin.before_request("POST", "https://api.example.com/second", json={"data": "test"})

        assert plugin.last_request["method"] == "POST"
        assert plugin.last_request["url"] == "https://api.example.com/second"


class TestRetryPluginAfterResponse:
    """Test after_response hook."""

    def test_after_response_resets_retry_count(self):
        """Test that after_response resets retry_count to 0."""
        plugin = RetryPlugin()
        plugin.retry_count = 5  # Simulate some retries

        response = Mock(spec=requests.Response)
        response.status_code = 200

        result = plugin.after_response(response)

        assert result == response
        assert plugin.retry_count == 0

    def test_after_response_with_201_status(self):
        """Test after_response with 201 status."""
        plugin = RetryPlugin()
        plugin.retry_count = 3

        response = Mock(spec=requests.Response)
        response.status_code = 201

        plugin.after_response(response)

        assert plugin.retry_count == 0

    def test_after_response_preserves_response(self):
        """Test that after_response returns the same response object."""
        plugin = RetryPlugin()

        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.text = "test data"

        result = plugin.after_response(response)

        assert result is response
        assert result.status_code == 200
        assert result.text == "test data"


class TestRetryPluginOnError:
    """Test on_error hook and retry logic."""

    @patch("time.sleep")
    def test_on_error_increments_retry_count(self, mock_sleep):
        """Test that on_error increments retry_count."""
        plugin = RetryPlugin()
        error = HTTPClientException("Server error")

        plugin.on_error(error)

        assert plugin.retry_count == 1

    @patch("time.sleep")
    def test_on_error_calculates_backoff_correctly(self, mock_sleep):
        """Test exponential backoff calculation."""
        plugin = RetryPlugin(backoff_factor=1.0)
        error = HTTPClientException("Server error")

        # First retry: 1.0 * 2^0 = 1.0
        plugin.on_error(error)
        mock_sleep.assert_called_with(1.0)

        # Second retry: 1.0 * 2^1 = 2.0
        plugin.on_error(error)
        mock_sleep.assert_called_with(2.0)

        # Third retry: 1.0 * 2^2 = 4.0
        plugin.on_error(error)
        mock_sleep.assert_called_with(4.0)

    @patch("time.sleep")
    def test_on_error_with_custom_backoff_factor(self, mock_sleep):
        """Test backoff with custom backoff_factor."""
        plugin = RetryPlugin(backoff_factor=0.5)
        error = HTTPClientException("Server error")

        # First retry: 0.5 * 2^0 = 0.5
        plugin.on_error(error)
        mock_sleep.assert_called_with(0.5)

        # Second retry: 0.5 * 2^1 = 1.0
        plugin.on_error(error)
        mock_sleep.assert_called_with(1.0)

    @patch("time.sleep")
    def test_on_error_max_retries_reached(self, mock_sleep):
        """Test behavior when max retries is reached."""
        plugin = RetryPlugin(max_retries=2)
        error = HTTPClientException("Server error")

        # First retry
        plugin.on_error(error)
        assert plugin.retry_count == 1

        # Second retry
        plugin.on_error(error)
        assert plugin.retry_count == 2

        # Third attempt - exceeds max_retries
        plugin.on_error(error)
        assert plugin.retry_count == 0  # Reset after max retries

    @patch("time.sleep")
    def test_on_error_resets_after_max_retries(self, mock_sleep):
        """Test that retry_count resets after exceeding max_retries."""
        plugin = RetryPlugin(max_retries=1)
        error = HTTPClientException("Server error")

        plugin.on_error(error)  # retry_count = 1
        assert plugin.retry_count == 1

        plugin.on_error(error)  # retry_count = 2, exceeds max_retries, resets
        assert plugin.retry_count == 0

    @patch("time.sleep")
    @patch("builtins.print")
    def test_on_error_prints_retry_message(self, mock_print, mock_sleep):
        """Test that on_error prints retry messages."""
        plugin = RetryPlugin(max_retries=3, backoff_factor=1.0)
        error = HTTPClientException("Server error")

        plugin.on_error(error)

        # Should print "Retry 1/3 after 1.0s..."
        mock_print.assert_called_with("Retry 1/3 after 1.0s...")

    @patch("time.sleep")
    @patch("builtins.print")
    def test_on_error_prints_max_retries_message(self, mock_print, mock_sleep):
        """Test that on_error prints max retries message."""
        plugin = RetryPlugin(max_retries=1)
        error = HTTPClientException("Server error")

        plugin.on_error(error)  # First retry
        plugin.on_error(error)  # Exceeds max_retries

        # Should print "Max retries (1) reached. Giving up."
        mock_print.assert_called_with("Max retries (1) reached. Giving up.")

    @patch("time.sleep")
    def test_on_error_with_zero_backoff(self, mock_sleep):
        """Test that zero backoff doesn't sleep."""
        plugin = RetryPlugin(backoff_factor=0.0)
        error = HTTPClientException("Server error")

        plugin.on_error(error)

        mock_sleep.assert_called_with(0.0)

    @patch("time.sleep")
    def test_on_error_with_different_exception_types(self, mock_sleep):
        """Test on_error with different exception types."""
        plugin = RetryPlugin()

        # Test with different exception types
        plugin.on_error(HTTPClientException("HTTP error"))
        assert plugin.retry_count == 1

        plugin.retry_count = 0  # Reset

        plugin.on_error(requests.RequestException("Request error"))
        assert plugin.retry_count == 1

        plugin.retry_count = 0  # Reset

        plugin.on_error(Exception("Generic error"))
        assert plugin.retry_count == 1


class TestRetryPluginRetryFlow:
    """Test complete retry flow scenarios."""

    @patch("time.sleep")
    def test_successful_request_after_error(self, mock_sleep):
        """Test that retry_count resets after successful request following errors."""
        plugin = RetryPlugin()
        error = HTTPClientException("Temporary error")
        response = Mock(spec=requests.Response)
        response.status_code = 200

        # Simulate error
        plugin.on_error(error)
        assert plugin.retry_count == 1

        # Simulate successful response
        plugin.after_response(response)
        assert plugin.retry_count == 0

    @patch("time.sleep")
    def test_multiple_error_cycles(self, mock_sleep):
        """Test multiple cycles of errors and successes."""
        plugin = RetryPlugin(max_retries=2)
        error = HTTPClientException("Error")
        response = Mock(spec=requests.Response)
        response.status_code = 200

        # First cycle: error -> error -> success
        plugin.on_error(error)
        plugin.on_error(error)
        plugin.after_response(response)
        assert plugin.retry_count == 0

        # Second cycle: error -> success
        plugin.on_error(error)
        assert plugin.retry_count == 1
        plugin.after_response(response)
        assert plugin.retry_count == 0

    @patch("time.sleep")
    def test_last_request_persistence(self, mock_sleep):
        """Test that last_request persists through retries."""
        plugin = RetryPlugin()
        kwargs = {"headers": {"X-Custom": "header"}}
        error = HTTPClientException("Error")

        # Save request
        plugin.before_request("GET", "https://api.example.com/test", **kwargs)

        # Trigger retries
        plugin.on_error(error)
        plugin.on_error(error)

        # Verify last_request is still saved
        assert plugin.last_request["method"] == "GET"
        assert plugin.last_request["url"] == "https://api.example.com/test"
        assert plugin.last_request["kwargs"] == kwargs


class TestRetryPluginEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_retry_count_never_negative(self):
        """Test that retry_count never goes negative."""
        plugin = RetryPlugin()
        response = Mock(spec=requests.Response)
        response.status_code = 200

        # Call after_response multiple times
        plugin.after_response(response)
        plugin.after_response(response)

        assert plugin.retry_count == 0

    @patch("time.sleep")
    def test_very_large_max_retries(self, mock_sleep):
        """Test with very large max_retries value."""
        plugin = RetryPlugin(max_retries=1000)
        error = HTTPClientException("Error")

        for i in range(5):
            plugin.on_error(error)

        assert plugin.retry_count == 5

    @patch("time.sleep")
    def test_very_large_backoff_factor(self, mock_sleep):
        """Test with very large backoff_factor."""
        plugin = RetryPlugin(backoff_factor=100.0)
        error = HTTPClientException("Error")

        plugin.on_error(error)

        # Should sleep for 100.0 * 2^0 = 100.0
        mock_sleep.assert_called_with(100.0)

    @patch("time.sleep")
    def test_backoff_growth_rate(self, mock_sleep):
        """Test that backoff time grows exponentially."""
        plugin = RetryPlugin(backoff_factor=1.0, max_retries=10)
        error = HTTPClientException("Error")

        expected_times = [1.0, 2.0, 4.0, 8.0, 16.0]

        for expected_time in expected_times:
            plugin.on_error(error)
            mock_sleep.assert_called_with(expected_time)
