"""
Tests for HTTPClientLogger.

Tests HTTPClientLogger, get_logger, and configure_logging.
"""

import logging
import os
import tempfile
import pytest

from src.http_client.core.logging.logger import (
    HTTPClientLogger,
    get_logger,
    configure_logging,
    _default_logger
)
from src.http_client.core.logging.config import LoggingConfig, LogLevel, LogFormat
from src.http_client.core.logging.filters import set_correlation_id, clear_correlation_id


class TestHTTPClientLogger:
    """Tests for HTTPClientLogger class."""

    def setup_method(self):
        """Reset logger before each test."""
        # Reset global logger
        import src.http_client.core.logging.logger as logger_module
        logger_module._default_logger = None
        clear_correlation_id()

    def test_logger_creation_with_defaults(self):
        """HTTPClientLogger can be created with defaults."""
        logger = HTTPClientLogger()

        assert logger.name == "http_client"
        assert logger.config.level == LogLevel.INFO
        assert logger.config.format == LogFormat.TEXT

    def test_logger_creation_with_custom_config(self):
        """HTTPClientLogger accepts custom config."""
        config = LoggingConfig.create(
            level="DEBUG",
            format="json"
        )
        logger = HTTPClientLogger(config=config)

        assert logger.config.level == LogLevel.DEBUG
        assert logger.config.format == LogFormat.JSON

    def test_logger_creation_with_custom_name(self):
        """HTTPClientLogger accepts custom name."""
        logger = HTTPClientLogger(name="custom_logger")

        assert logger.name == "custom_logger"

    def test_logger_has_internal_logger(self):
        """HTTPClientLogger has internal Python logger."""
        logger = HTTPClientLogger()

        assert hasattr(logger, "_logger")
        assert isinstance(logger._logger, logging.Logger)

    def test_logger_propagate_is_false(self):
        """Logger does not propagate to root logger."""
        logger = HTTPClientLogger()

        assert logger._logger.propagate is False

    def test_logger_level_is_set(self):
        """Logger level is set from config."""
        config = LoggingConfig.create(level="WARNING")
        logger = HTTPClientLogger(config=config)

        assert logger._logger.level == logging.WARNING

    def test_logger_has_console_handler(self):
        """Logger has console handler when enabled."""
        config = LoggingConfig.create(enable_console=True)
        logger = HTTPClientLogger(config=config)

        assert len(logger._logger.handlers) >= 1
        assert any(isinstance(h, logging.StreamHandler) for h in logger._logger.handlers)

    def test_logger_no_console_handler_when_disabled(self):
        """Logger has no console handler when disabled."""
        config = LoggingConfig.create(enable_console=False, enable_file=False)
        logger = HTTPClientLogger(config=config)

        assert len(logger._logger.handlers) == 0

    def test_logger_has_file_handler(self):
        """Logger has file handler when enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            config = LoggingConfig.create(
                enable_console=False,
                enable_file=True,
                file_path=log_file
            )
            logger = HTTPClientLogger(config=config)

            assert len(logger._logger.handlers) == 1
            from logging.handlers import RotatingFileHandler
            assert isinstance(logger._logger.handlers[0], RotatingFileHandler)

            # Cleanup
            for handler in logger._logger.handlers:
                handler.close()

    def test_logger_debug_method(self):
        """Logger has debug() method."""
        logger = HTTPClientLogger()

        # Should not raise
        logger.debug("Debug message")

    def test_logger_info_method(self):
        """Logger has info() method."""
        logger = HTTPClientLogger()

        # Should not raise
        logger.info("Info message")

    def test_logger_warning_method(self):
        """Logger has warning() method."""
        logger = HTTPClientLogger()

        # Should not raise
        logger.warning("Warning message")

    def test_logger_error_method(self):
        """Logger has error() method."""
        logger = HTTPClientLogger()

        # Should not raise
        logger.error("Error message")

    def test_logger_critical_method(self):
        """Logger has critical() method."""
        logger = HTTPClientLogger()

        # Should not raise
        logger.critical("Critical message")

    def test_logger_exception_method(self):
        """Logger has exception() method."""
        logger = HTTPClientLogger()

        try:
            raise ValueError("Test error")
        except ValueError:
            # Should not raise
            logger.exception("Exception occurred")

    def test_logger_methods_accept_kwargs(self):
        """Logger methods accept extra kwargs."""
        logger = HTTPClientLogger()

        # Should not raise
        logger.info("Message", user_id=123, action="login")
        logger.debug("Debug", request_id="req-456")
        logger.error("Error", error_code=500)

    def test_logger_writes_to_file(self):
        """Logger actually writes logs to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            config = LoggingConfig.create(
                enable_console=False,
                enable_file=True,
                file_path=log_file,
                format="text"
            )
            logger = HTTPClientLogger(config=config)

            logger.info("Test log entry")

            # Close handlers to flush
            for handler in logger._logger.handlers:
                handler.close()

            # Check file
            assert os.path.exists(log_file)
            with open(log_file, 'r') as f:
                content = f.read()
                assert "Test log entry" in content

    def test_logger_with_correlation_id_filter(self):
        """Logger includes correlation ID when enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            config = LoggingConfig.create(
                enable_console=False,
                enable_file=True,
                file_path=log_file,
                format="json",
                enable_correlation_id=True
            )
            logger = HTTPClientLogger(config=config)

            set_correlation_id("test-correlation-123")
            logger.info("Message with correlation")

            # Close handlers
            for handler in logger._logger.handlers:
                handler.close()

            # Check file
            with open(log_file, 'r') as f:
                content = f.read()
                assert "test-correlation-123" in content

            clear_correlation_id()

    def test_logger_with_extra_fields(self):
        """Logger includes extra fields when configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            config = LoggingConfig.create(
                enable_console=False,
                enable_file=True,
                file_path=log_file,
                format="json",
                extra_fields={"service": "api", "version": "1.0.0"}
            )
            logger = HTTPClientLogger(config=config)

            logger.info("Test message")

            # Close handlers
            for handler in logger._logger.handlers:
                handler.close()

            # Check file
            with open(log_file, 'r') as f:
                content = f.read()
                assert "api" in content
                assert "1.0.0" in content

    def test_logger_clears_existing_handlers(self):
        """Logger clears existing handlers on initialization."""
        logger1 = HTTPClientLogger(name="test_clear")
        handler_count1 = len(logger1._logger.handlers)

        # Create another logger with same name
        logger2 = HTTPClientLogger(name="test_clear")
        handler_count2 = len(logger2._logger.handlers)

        # Should have same number of handlers (not doubled)
        assert handler_count1 == handler_count2


class TestGetLogger:
    """Tests for get_logger() function."""

    def setup_method(self):
        """Reset global logger before each test."""
        import src.http_client.core.logging.logger as logger_module
        logger_module._default_logger = None

    def test_get_logger_returns_instance(self):
        """get_logger() returns HTTPClientLogger instance."""
        logger = get_logger()

        assert isinstance(logger, HTTPClientLogger)

    def test_get_logger_returns_same_instance(self):
        """get_logger() returns same instance (singleton)."""
        logger1 = get_logger()
        logger2 = get_logger()

        assert logger1 is logger2

    def test_get_logger_with_config(self):
        """get_logger() accepts config on first call."""
        config = LoggingConfig.create(level="DEBUG", format="json")
        logger = get_logger(config)

        assert logger.config.level == LogLevel.DEBUG
        assert logger.config.format == LogFormat.JSON

    def test_get_logger_config_ignored_on_subsequent_calls(self):
        """get_logger() ignores config on subsequent calls."""
        config1 = LoggingConfig.create(level="INFO")
        logger1 = get_logger(config1)

        config2 = LoggingConfig.create(level="DEBUG")
        logger2 = get_logger(config2)

        # Should be same instance with original config
        assert logger1 is logger2
        assert logger2.config.level == LogLevel.INFO

    def test_get_logger_uses_defaults_if_no_config(self):
        """get_logger() uses default config if none provided."""
        logger = get_logger()

        assert logger.config.level == LogLevel.INFO
        assert logger.config.format == LogFormat.TEXT


class TestConfigureLogging:
    """Tests for configure_logging() function."""

    def setup_method(self):
        """Reset global logger before each test."""
        import src.http_client.core.logging.logger as logger_module
        logger_module._default_logger = None

    def test_configure_logging_creates_new_logger(self):
        """configure_logging() creates new logger."""
        config = LoggingConfig.create(level="DEBUG")
        logger = configure_logging(config)

        assert isinstance(logger, HTTPClientLogger)
        assert logger.config.level == LogLevel.DEBUG

    def test_configure_logging_replaces_existing_logger(self):
        """configure_logging() replaces existing logger."""
        config1 = LoggingConfig.create(level="INFO")
        logger1 = get_logger(config1)

        config2 = LoggingConfig.create(level="ERROR")
        logger2 = configure_logging(config2)

        # Should be different instance with new config
        assert logger2.config.level == LogLevel.ERROR

        # get_logger() should now return the new logger
        logger3 = get_logger()
        assert logger3 is logger2

    def test_configure_logging_always_uses_provided_config(self):
        """configure_logging() always uses provided config."""
        config1 = LoggingConfig.create(level="WARNING")
        configure_logging(config1)

        config2 = LoggingConfig.create(level="CRITICAL")
        logger = configure_logging(config2)

        assert logger.config.level == LogLevel.CRITICAL


class TestLoggerIntegration:
    """Integration tests for logger."""

    def setup_method(self):
        """Reset logger before each test."""
        import src.http_client.core.logging.logger as logger_module
        logger_module._default_logger = None
        clear_correlation_id()

    def test_full_logging_workflow(self):
        """Test complete logging workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "app.log")

            # Configure logger
            config = LoggingConfig.create(
                level="DEBUG",
                format="json",
                enable_console=False,
                enable_file=True,
                file_path=log_file,
                enable_correlation_id=True,
                extra_fields={"service": "test_service"}
            )

            logger = configure_logging(config)

            # Set correlation ID
            set_correlation_id("req-999")

            # Log various levels
            logger.debug("Debug message", step=1)
            logger.info("Info message", step=2)
            logger.warning("Warning message", step=3)
            logger.error("Error message", step=4)

            # Close handlers
            for handler in logger._logger.handlers:
                handler.close()

            # Verify file
            assert os.path.exists(log_file)
            with open(log_file, 'r') as f:
                lines = f.readlines()

                # Should have 4 log entries
                assert len(lines) == 4

                # Check first line
                import json
                first_log = json.loads(lines[0])
                assert first_log["level"] == "DEBUG"
                assert first_log["correlation_id"] == "req-999"
                assert first_log["service"] == "test_service"
                assert first_log["step"] == 1

            clear_correlation_id()
