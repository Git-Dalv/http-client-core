"""
Logging configuration for HTTP Client.

Provides configuration classes for structured logging.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any


class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """Log output formats."""
    JSON = "json"
    TEXT = "text"
    COLORED = "colored"


@dataclass(frozen=True)
class LoggingConfig:
    """
    Configuration for HTTP Client logging.

    Attributes:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: Output format (json, text, colored)
        enable_console: Enable console (stdout) logging
        enable_file: Enable file logging
        file_path: Path to log file (required if enable_file=True)
        max_bytes: Max log file size before rotation (default: 10MB)
        backup_count: Number of backup log files to keep (default: 5)
        enable_correlation_id: Add correlation ID to logs
        extra_fields: Additional fields to add to every log entry

    Example:
        >>> config = LoggingConfig.create(
        ...     level="INFO",
        ...     format="colored",
        ...     enable_file=True,
        ...     file_path="/var/log/app.log"
        ... )
    """

    level: LogLevel = LogLevel.INFO
    format: LogFormat = LogFormat.TEXT
    enable_console: bool = True
    enable_file: bool = False
    file_path: Optional[str] = None
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    enable_correlation_id: bool = True
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        level: str = "INFO",
        format: str = "text",
        enable_console: bool = True,
        enable_file: bool = False,
        file_path: Optional[str] = None,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
        enable_correlation_id: bool = True,
        extra_fields: Optional[Dict[str, Any]] = None
    ) -> "LoggingConfig":
        """
        Create LoggingConfig with string values.

        Args:
            level: Log level as string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format: Log format as string (json, text, colored)
            enable_console: Enable console logging
            enable_file: Enable file logging
            file_path: Path to log file
            max_bytes: Max file size before rotation
            backup_count: Number of backup files
            enable_correlation_id: Add correlation IDs
            extra_fields: Additional fields for logs

        Returns:
            LoggingConfig instance

        Example:
            >>> config = LoggingConfig.create(
            ...     level="DEBUG",
            ...     format="json",
            ...     enable_file=True,
            ...     file_path="/tmp/app.log"
            ... )
        """
        return cls(
            level=LogLevel(level.upper()),
            format=LogFormat(format.lower()),
            enable_console=enable_console,
            enable_file=enable_file,
            file_path=file_path,
            max_bytes=max_bytes,
            backup_count=backup_count,
            enable_correlation_id=enable_correlation_id,
            extra_fields=extra_fields or {}
        )
