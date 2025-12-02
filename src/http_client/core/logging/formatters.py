"""
Log formatters for different output formats.

Provides JSON, text, and colored formatters.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs logs as JSON objects with fields:
    - timestamp: ISO 8601 timestamp
    - level: Log level (DEBUG, INFO, etc.)
    - logger: Logger name
    - message: Log message
    - ... (any extra fields)

    Example output:
        {"timestamp": "2024-01-15T10:30:45.123Z", "level": "INFO",
         "logger": "http_client", "message": "Request started",
         "method": "GET", "url": "https://api.com"}
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields from record.__dict__
        # Skip standard logging fields
        skip_fields = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'message', 'pathname', 'process', 'processName', 'relativeCreated',
            'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info'
        }

        for key, value in record.__dict__.items():
            if key not in skip_fields and not key.startswith('_'):
                log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """
    Plain text formatter.

    Format: [timestamp] [level] [logger] message [extra_fields]

    Example output:
        [2024-01-15 10:30:45] [INFO] [http_client] Request started method=GET url=https://api.com
    """

    def __init__(self):
        """Initialize text formatter."""
        super().__init__(
            fmt='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as text."""
        # Format base message
        base_msg = super().format(record)

        # Add extra fields
        skip_fields = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'message', 'pathname', 'process', 'processName', 'relativeCreated',
            'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info',
            'asctime'
        }

        extra_fields = []
        for key, value in record.__dict__.items():
            if key not in skip_fields and not key.startswith('_'):
                extra_fields.append(f"{key}={value}")

        if extra_fields:
            base_msg += " " + " ".join(extra_fields)

        return base_msg


class ColoredFormatter(logging.Formatter):
    """
    Colored text formatter for terminal output.

    Uses ANSI color codes to colorize log levels:
    - DEBUG: Cyan
    - INFO: Green
    - WARNING: Yellow
    - ERROR: Red
    - CRITICAL: Red + Bold

    Example output (with colors):
        [2024-01-15 10:30:45] [INFO] [http_client] Request started method=GET
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[1;31m', # Bold Red
        'RESET': '\033[0m'        # Reset
    }

    def __init__(self):
        """Initialize colored formatter."""
        super().__init__(
            fmt='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"

        # Format base message
        base_msg = super().format(record)

        # Restore original levelname
        record.levelname = levelname

        # Add extra fields
        skip_fields = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'message', 'pathname', 'process', 'processName', 'relativeCreated',
            'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info',
            'asctime'
        }

        extra_fields = []
        for key, value in record.__dict__.items():
            if key not in skip_fields and not key.startswith('_'):
                extra_fields.append(f"{key}={value}")

        if extra_fields:
            base_msg += " " + " ".join(extra_fields)

        return base_msg


def get_formatter(format_type: str) -> logging.Formatter:
    """
    Get formatter by type.

    Args:
        format_type: Format type (json, text, colored)

    Returns:
        Formatter instance

    Raises:
        ValueError: If format_type is unknown

    Example:
        >>> formatter = get_formatter("json")
        >>> formatter = get_formatter("colored")
    """
    formatters = {
        "json": JSONFormatter,
        "text": TextFormatter,
        "colored": ColoredFormatter,
    }

    formatter_class = formatters.get(format_type.lower())
    if not formatter_class:
        raise ValueError(
            f"Unknown format type: {format_type}. "
            f"Available: {', '.join(formatters.keys())}"
        )

    return formatter_class()
