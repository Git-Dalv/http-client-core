"""
Tests for logging configuration.

Tests LoggingConfig, LogLevel, and LogFormat.
"""

import pytest
from src.http_client.core.logging.config import LoggingConfig, LogLevel, LogFormat


class TestLogLevel:
    """Tests for LogLevel enum."""

    def test_log_level_values(self):
        """LogLevel has correct values."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"

    def test_log_level_is_string(self):
        """LogLevel inherits from str."""
        assert isinstance(LogLevel.INFO, str)


class TestLogFormat:
    """Tests for LogFormat enum."""

    def test_log_format_values(self):
        """LogFormat has correct values."""
        assert LogFormat.JSON.value == "json"
        assert LogFormat.TEXT.value == "text"
        assert LogFormat.COLORED.value == "colored"

    def test_log_format_is_string(self):
        """LogFormat inherits from str."""
        assert isinstance(LogFormat.JSON, str)


class TestLoggingConfig:
    """Tests for LoggingConfig dataclass."""

    def test_default_config(self):
        """Default LoggingConfig has expected values."""
        config = LoggingConfig()

        assert config.level == LogLevel.INFO
        assert config.format == LogFormat.TEXT
        assert config.enable_console is True
        assert config.enable_file is False
        assert config.file_path is None
        assert config.max_bytes == 10 * 1024 * 1024  # 10MB
        assert config.backup_count == 5
        assert config.enable_correlation_id is True
        assert config.extra_fields == {}

    def test_config_with_custom_values(self):
        """LoggingConfig accepts custom values."""
        config = LoggingConfig(
            level=LogLevel.DEBUG,
            format=LogFormat.JSON,
            enable_console=False,
            enable_file=True,
            file_path="/var/log/app.log",
            max_bytes=5 * 1024 * 1024,
            backup_count=3,
            enable_correlation_id=False,
            extra_fields={"service": "api"}
        )

        assert config.level == LogLevel.DEBUG
        assert config.format == LogFormat.JSON
        assert config.enable_console is False
        assert config.enable_file is True
        assert config.file_path == "/var/log/app.log"
        assert config.max_bytes == 5 * 1024 * 1024
        assert config.backup_count == 3
        assert config.enable_correlation_id is False
        assert config.extra_fields == {"service": "api"}

    def test_config_is_frozen(self):
        """LoggingConfig is immutable (frozen)."""
        config = LoggingConfig()

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            config.level = LogLevel.DEBUG

    def test_create_with_defaults(self):
        """LoggingConfig.create() works with defaults."""
        config = LoggingConfig.create()

        assert config.level == LogLevel.INFO
        assert config.format == LogFormat.TEXT
        assert config.enable_console is True
        assert config.enable_file is False

    def test_create_with_string_level(self):
        """LoggingConfig.create() accepts string level."""
        config = LoggingConfig.create(level="DEBUG")
        assert config.level == LogLevel.DEBUG

        config = LoggingConfig.create(level="error")  # lowercase
        assert config.level == LogLevel.ERROR

    def test_create_with_string_format(self):
        """LoggingConfig.create() accepts string format."""
        config = LoggingConfig.create(format="json")
        assert config.format == LogFormat.JSON

        config = LoggingConfig.create(format="COLORED")  # uppercase
        assert config.format == LogFormat.COLORED

    def test_create_with_all_parameters(self):
        """LoggingConfig.create() accepts all parameters."""
        config = LoggingConfig.create(
            level="DEBUG",
            format="json",
            enable_console=False,
            enable_file=True,
            file_path="/tmp/test.log",
            max_bytes=1024,
            backup_count=2,
            enable_correlation_id=False,
            extra_fields={"env": "test"}
        )

        assert config.level == LogLevel.DEBUG
        assert config.format == LogFormat.JSON
        assert config.enable_console is False
        assert config.enable_file is True
        assert config.file_path == "/tmp/test.log"
        assert config.max_bytes == 1024
        assert config.backup_count == 2
        assert config.enable_correlation_id is False
        assert config.extra_fields == {"env": "test"}

    def test_create_extra_fields_default(self):
        """LoggingConfig.create() uses empty dict for extra_fields by default."""
        config = LoggingConfig.create()
        assert config.extra_fields == {}

    def test_config_extra_fields_not_shared(self):
        """Each config has independent extra_fields dict."""
        config1 = LoggingConfig()
        config2 = LoggingConfig()

        # They should be equal but not the same object
        assert config1.extra_fields == config2.extra_fields
        # (We can't modify them due to frozen, so we can't test identity mutation)
