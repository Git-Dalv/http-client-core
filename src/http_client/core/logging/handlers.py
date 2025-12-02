"""
Log handlers for file and console output.

Provides handlers with rotation, filtering, and formatting.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, List


def create_console_handler(
    level: int,
    formatter: logging.Formatter,
    filters: Optional[List[logging.Filter]] = None
) -> logging.StreamHandler:
    """
    Create console (stdout) handler.

    Args:
        level: Log level (e.g. logging.INFO)
        formatter: Formatter instance
        filters: List of filters to add

    Returns:
        StreamHandler configured for console

    Example:
        >>> from .formatters import ColoredFormatter
        >>> import logging
        >>> formatter = ColoredFormatter()
        >>> handler = create_console_handler(logging.INFO, formatter)
        >>> logger = logging.getLogger("my_app")
        >>> logger.addHandler(handler)
        >>> logger.info("Hello, World!")
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)

    if filters:
        for f in filters:
            handler.addFilter(f)

    return handler


def create_file_handler(
    file_path: str,
    level: int,
    formatter: logging.Formatter,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    filters: Optional[List[logging.Filter]] = None
) -> RotatingFileHandler:
    """
    Create rotating file handler.

    Automatically rotates log file when it reaches max_bytes.
    Keeps backup_count old files.

    Args:
        file_path: Path to log file
        level: Log level
        formatter: Formatter instance
        max_bytes: Max file size before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
        filters: List of filters to add

    Returns:
        RotatingFileHandler instance

    Example:
        >>> from .formatters import JSONFormatter
        >>> import logging
        >>> formatter = JSONFormatter()
        >>> handler = create_file_handler(
        ...     "/var/log/app.log",
        ...     logging.INFO,
        ...     formatter,
        ...     max_bytes=10*1024*1024,  # 10MB
        ...     backup_count=5
        ... )
        >>> logger = logging.getLogger("my_app")
        >>> logger.addHandler(handler)
        >>> logger.info("Logged to file")

    File rotation:
        app.log       <- current
        app.log.1     <- previous
        app.log.2     <- older
        ...
        app.log.5     <- oldest (deleted when new rotation happens)
    """
    # Create directory if it doesn't exist
    log_dir = Path(file_path).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        filename=file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    handler.setLevel(level)
    handler.setFormatter(formatter)

    if filters:
        for f in filters:
            handler.addFilter(f)

    return handler
