"""
Logging system for HTTP Client.

Provides structured logging with multiple formats, handlers, and filters.

Example:
    >>> from http_client.core.logging import get_logger, LoggingConfig
    >>>
    >>> # Quick start with defaults
    >>> logger = get_logger()
    >>> logger.info("Hello, World!")
    >>>
    >>> # Configure logging
    >>> config = LoggingConfig.create(
    ...     level="DEBUG",
    ...     format="colored",
    ...     enable_file=True,
    ...     file_path="/var/log/app.log"
    ... )
    >>> logger = get_logger(config)
    >>> logger.info("Request started", method="GET", url="https://api.com")
"""

from .config import LoggingConfig, LogLevel, LogFormat
from .logger import HTTPClientLogger, get_logger, configure_logging
from .formatters import JSONFormatter, TextFormatter, ColoredFormatter, get_formatter
from .filters import (
    CorrelationIdFilter,
    ExtraFieldsFilter,
    RequestContextFilter,
    set_correlation_id,
    get_correlation_id,
    clear_correlation_id,
)
from .handlers import create_console_handler, create_file_handler

__all__ = [
    # Config
    "LoggingConfig",
    "LogLevel",
    "LogFormat",
    # Logger
    "HTTPClientLogger",
    "get_logger",
    "configure_logging",
    # Formatters
    "JSONFormatter",
    "TextFormatter",
    "ColoredFormatter",
    "get_formatter",
    # Filters
    "CorrelationIdFilter",
    "ExtraFieldsFilter",
    "RequestContextFilter",
    "set_correlation_id",
    "get_correlation_id",
    "clear_correlation_id",
    # Handlers
    "create_console_handler",
    "create_file_handler",
]
