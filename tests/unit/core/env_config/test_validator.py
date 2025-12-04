"""
Tests for Pydantic validators.
"""

import pytest
import os
import tempfile
from pydantic import ValidationError
from src.http_client.core.env_config.validator import (
    HTTPClientSettings,
    TimeoutSettings,
    RetrySettings,
    SecuritySettings,
    PoolSettings,
    LoggingSettings,
)


class TestTimeoutSettings:
    """Test TimeoutSettings validator."""

    def test_valid_timeouts(self):
        """Test valid timeout settings."""
        settings = TimeoutSettings(connect=5.0, read=10.0, total=30.0)
        assert settings.connect == 5.0
        assert settings.read == 10.0
        assert settings.total == 30.0

    def test_total_must_be_greater_than_sum(self):
        """Test that total >= connect + read."""
        with pytest.raises(ValidationError):
            TimeoutSettings(connect=10.0, read=15.0, total=20.0)  # 20 < 10+15


class TestRetrySettings:
    """Test RetrySettings validator."""

    def test_valid_retry(self):
        """Test valid retry settings."""
        settings = RetrySettings(max_attempts=3, backoff_factor=2.0)
        assert settings.max_attempts == 3
        assert settings.backoff_factor == 2.0

    def test_max_attempts_bounds(self):
        """Test max_attempts bounds."""
        with pytest.raises(ValidationError):
            RetrySettings(max_attempts=0)  # Too low
        with pytest.raises(ValidationError):
            RetrySettings(max_attempts=11)  # Too high


class TestHTTPClientSettings:
    """Test HTTPClientSettings main class."""

    def test_defaults(self):
        """Test default values."""
        settings = HTTPClientSettings()
        assert settings.base_url == ""
        assert settings.timeout_connect == 5.0
        assert settings.retry_max_attempts == 3

    def test_from_env_file(self):
        """Test loading from .env file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as f:
            f.write("HTTP_CLIENT_BASE_URL=https://test.com\n")
            f.write("HTTP_CLIENT_TIMEOUT_CONNECT=10.0\n")
            env_file = f.name

        try:
            settings = HTTPClientSettings(_env_file=env_file)
            assert settings.base_url == "https://test.com"
            assert settings.timeout_connect == 10.0
        finally:
            os.remove(env_file)

    def test_api_key_validation(self):
        """Test API key length validation."""
        with pytest.raises(ValidationError):
            HTTPClientSettings(api_key="short")  # Less than 8 chars

    def test_to_timeout_settings(self):
        """Test conversion to TimeoutSettings."""
        settings = HTTPClientSettings(timeout_connect=7.0, timeout_read=15.0)
        timeout_settings = settings.to_timeout_settings()
        assert isinstance(timeout_settings, TimeoutSettings)
        assert timeout_settings.connect == 7.0

    def test_to_logging_settings(self):
        """Test conversion to LoggingSettings."""
        settings = HTTPClientSettings(log_enable_console=True)
        logging_settings = settings.to_logging_settings()
        assert logging_settings is not None
        assert logging_settings.enable_console is True

    def test_logging_disabled_when_all_false(self):
        """Test logging disabled when all outputs disabled."""
        settings = HTTPClientSettings(log_enable_console=False, log_enable_file=False)
        assert settings.to_logging_settings() is None
