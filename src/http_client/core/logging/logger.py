"""
Main logger for HTTP Client.

Provides easy-to-use logger with multiple handlers, formatters, and filters.
"""

import logging
from typing import Optional, Any

from .config import LoggingConfig, LogLevel, LogFormat
from .formatters import get_formatter
from .filters import CorrelationIdFilter, ExtraFieldsFilter
from .handlers import create_console_handler, create_file_handler
from ...utils.sanitizer import mask_sensitive_data


class HTTPClientLogger:
    """
    Main logger for HTTP Client.

    Features:
    - Multiple handlers (console, file)
    - Multiple formatters (JSON, text, colored)
    - Correlation ID support
    - Extra fields support
    - Easy configuration

    Example:
        >>> from .config import LoggingConfig
        >>> config = LoggingConfig.create(
        ...     level="INFO",
        ...     format="colored",
        ...     enable_file=True,
        ...     file_path="/var/log/app.log"
        ... )
        >>> logger = HTTPClientLogger(config)
        >>> logger.info("Request started", method="GET", url="https://api.com")
    """

    def __init__(self, config: Optional[LoggingConfig] = None, name: str = "http_client"):
        """
        Initialize logger.

        Args:
            config: Logging configuration (uses defaults if None)
            name: Logger name

        Example:
            >>> logger = HTTPClientLogger()  # Uses defaults
            >>> logger.info("Hello, World!")
        """
        self.config = config or LoggingConfig()
        self.name = name
        self._closed = False

        # Create Python logger
        self._logger = logging.getLogger(name)
        self._logger.setLevel(self._get_level(self.config.level))
        self._logger.propagate = False  # Don't propagate to root logger

        # Remove existing handlers (if reinitializing)
        self._logger.handlers.clear()

        # Create filters
        filters = []

        if self.config.enable_correlation_id:
            filters.append(CorrelationIdFilter())

        if self.config.extra_fields:
            filters.append(ExtraFieldsFilter(self.config.extra_fields))

        # Create formatter
        formatter = get_formatter(self.config.format.value)

        # Add console handler
        if self.config.enable_console:
            console_handler = create_console_handler(
                level=self._get_level(self.config.level),
                formatter=formatter,
                filters=filters
            )
            self._logger.addHandler(console_handler)

        # Add file handler
        if self.config.enable_file and self.config.file_path:
            file_handler = create_file_handler(
                file_path=self.config.file_path,
                level=self._get_level(self.config.level),
                formatter=formatter,
                max_bytes=self.config.max_bytes,
                backup_count=self.config.backup_count,
                filters=filters
            )
            self._logger.addHandler(file_handler)

    def _get_level(self, level: LogLevel) -> int:
        """
        Convert LogLevel enum to logging level int.

        Args:
            level: LogLevel enum value

        Returns:
            Logging level integer (e.g. logging.INFO)
        """
        return getattr(logging, level.value)

    # Proxy methods for convenient logging

    def debug(self, message: str, **kwargs: Any) -> None:
        """
        Log debug message.

        Args:
            message: Log message
            **kwargs: Extra fields to add to log

        Example:
            >>> logger.debug("Processing data", item_count=100)
        """
        sanitized_kwargs = mask_sensitive_data(kwargs)
        self._logger.debug(message, extra=sanitized_kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """
        Log info message.

        Args:
            message: Log message
            **kwargs: Extra fields to add to log

        Example:
            >>> logger.info("Request completed", status_code=200, duration_ms=150)
        """
        sanitized_kwargs = mask_sensitive_data(kwargs)
        self._logger.info(message, extra=sanitized_kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """
        Log warning message.

        Args:
            message: Log message
            **kwargs: Extra fields to add to log

        Example:
            >>> logger.warning("Slow response", duration_ms=5000)
        """
        sanitized_kwargs = mask_sensitive_data(kwargs)
        self._logger.warning(message, extra=sanitized_kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """
        Log error message.

        Args:
            message: Log message
            **kwargs: Extra fields to add to log

        Example:
            >>> logger.error("Request failed", status_code=500, error="Internal Server Error")
        """
        sanitized_kwargs = mask_sensitive_data(kwargs)
        self._logger.error(message, extra=sanitized_kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """
        Log critical message.

        Args:
            message: Log message
            **kwargs: Extra fields to add to log

        Example:
            >>> logger.critical("Service unavailable", service="database")
        """
        sanitized_kwargs = mask_sensitive_data(kwargs)
        self._logger.critical(message, extra=sanitized_kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        """
        Log exception with traceback.

        Should be called from an exception handler.

        Args:
            message: Log message
            **kwargs: Extra fields to add to log

        Example:
            >>> try:
            ...     risky_operation()
            ... except Exception:
            ...     logger.exception("Operation failed", operation="risky_operation")
        """
        sanitized_kwargs = mask_sensitive_data(kwargs)
        self._logger.exception(message, extra=sanitized_kwargs)

    def close(self) -> None:
        """
        Close all handlers and release resources.

        This method should be called when the logger is no longer needed,
        especially when file handlers are used. It ensures proper cleanup
        of file descriptors and other resources.

        This method is idempotent - it can be safely called multiple times.

        Example:
            >>> logger = HTTPClientLogger(config)
            >>> logger.info("Processing...")
            >>> logger.close()  # Release resources
            >>> logger.close()  # Safe to call again

            >>> # Or use as context manager
            >>> with HTTPClientLogger(config) as logger:
            ...     logger.info("Processing...")
            >>> # Automatically closed
        """
        if self._closed:
            return  # Already closed

        # Flush and close all handlers
        for handler in self._logger.handlers[:]:  # Copy list to avoid modification during iteration
            try:
                # Flush any buffered data
                handler.flush()
            except Exception:
                # Ignore flush errors
                pass

            try:
                # Close the handler
                handler.close()
            except Exception:
                # Ignore close errors
                pass

            try:
                # Remove from logger
                self._logger.removeHandler(handler)
            except Exception:
                # Ignore removal errors
                pass

        # Clear the handlers list
        self._logger.handlers.clear()

        # Mark as closed
        self._closed = True

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close logger on context exit."""
        self.close()
        return False


# Global logger instance (singleton pattern)
_default_logger: Optional[HTTPClientLogger] = None


def get_logger(config: Optional[LoggingConfig] = None) -> HTTPClientLogger:
    """
    Get global logger instance.

    Creates new logger if not exists, or returns existing one.

    Args:
        config: Logging configuration (only used on first call)

    Returns:
        HTTPClientLogger instance

    Example:
        >>> logger = get_logger()
        >>> logger.info("Hello")

        >>> # Configure once
        >>> config = LoggingConfig.create(level="DEBUG", format="json")
        >>> logger = get_logger(config)
    """
    global _default_logger

    if _default_logger is None:
        _default_logger = HTTPClientLogger(config)

    return _default_logger


def configure_logging(config: LoggingConfig) -> HTTPClientLogger:
    """
    Configure global logger.

    Replaces existing logger with new configuration.

    Args:
        config: Logging configuration

    Returns:
        New HTTPClientLogger instance

    Example:
        >>> config = LoggingConfig.create(
        ...     level="DEBUG",
        ...     format="colored",
        ...     enable_file=True,
        ...     file_path="/tmp/app.log"
        ... )
        >>> logger = configure_logging(config)
        >>> logger.info("Logger configured")
    """
    global _default_logger
    _default_logger = HTTPClientLogger(config)
    return _default_logger
