"""
Log filters for adding context and filtering logs.

Provides filters for correlation IDs, extra fields, and request context.
"""

import logging
import threading
from typing import Dict, Any, Optional


# Thread-local storage for correlation ID
_correlation_id_storage = threading.local()


def set_correlation_id(correlation_id: str) -> None:
    """
    Set correlation ID for current thread.

    Args:
        correlation_id: Correlation ID string

    Example:
        >>> set_correlation_id("req-12345")
        >>> logger.info("Processing request")  # Will include correlation_id
    """
    _correlation_id_storage.value = correlation_id


def get_correlation_id() -> Optional[str]:
    """
    Get correlation ID for current thread.

    Returns:
        Correlation ID or None if not set

    Example:
        >>> set_correlation_id("req-12345")
        >>> get_correlation_id()
        'req-12345'
    """
    return getattr(_correlation_id_storage, 'value', None)


def clear_correlation_id() -> None:
    """
    Clear correlation ID for current thread.

    Example:
        >>> set_correlation_id("req-12345")
        >>> clear_correlation_id()
        >>> get_correlation_id()
        None
    """
    if hasattr(_correlation_id_storage, 'value'):
        delattr(_correlation_id_storage, 'value')


class CorrelationIdFilter(logging.Filter):
    """
    Filter that adds correlation ID to log records.

    Retrieves correlation ID from thread-local storage and adds it
    to every log record.

    Example:
        >>> from .filters import CorrelationIdFilter, set_correlation_id
        >>> filter = CorrelationIdFilter()
        >>> handler.addFilter(filter)
        >>>
        >>> set_correlation_id("req-12345")
        >>> logger.info("Request started")  # Will include correlation_id=req-12345
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to record if present."""
        correlation_id = get_correlation_id()
        if correlation_id:
            record.correlation_id = correlation_id
        return True


class ExtraFieldsFilter(logging.Filter):
    """
    Filter that adds extra static fields to all log records.

    Useful for adding environment, service name, version, etc.

    Example:
        >>> filter = ExtraFieldsFilter({
        ...     "service": "api",
        ...     "environment": "production",
        ...     "version": "1.0.0"
        ... })
        >>> handler.addFilter(filter)
        >>> logger.info("Started")  # Will include service, environment, version
    """

    def __init__(self, extra_fields: Dict[str, Any]):
        """
        Initialize filter with extra fields.

        Args:
            extra_fields: Dictionary of fields to add to every log
        """
        super().__init__()
        self.extra_fields = extra_fields

    def filter(self, record: logging.LogRecord) -> bool:
        """Add extra fields to record."""
        for key, value in self.extra_fields.items():
            if not hasattr(record, key):
                setattr(record, key, value)
        return True


class RequestContextFilter(logging.Filter):
    """
    Filter that adds HTTP request context to logs.

    Automatically extracts and adds:
    - method (GET, POST, etc.)
    - url
    - status_code
    - duration_ms

    Expects these fields in LogRecord (passed via extra parameter).

    Example:
        >>> filter = RequestContextFilter()
        >>> handler.addFilter(filter)
        >>> logger.info("Request completed", extra={
        ...     "method": "GET",
        ...     "url": "https://api.com",
        ...     "status_code": 200,
        ...     "duration_ms": 150
        ... })
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add HTTP context if present.

        The filter checks if HTTP context fields are present in the record
        (passed via extra parameter). If they are, they remain in the log.
        If not, nothing is added.

        Always returns True to pass the log record through.
        """
        # This filter is passive - it doesn't add fields, just ensures
        # they pass through if present. The fields are added by passing
        # them in the extra parameter when logging.

        # We could add validation here if needed:
        # if hasattr(record, 'method') and hasattr(record, 'url'):
        #     # Valid HTTP context
        #     pass

        return True
