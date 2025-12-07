"""HTTP Client Library - Production-ready HTTP client with plugins."""

import logging

from .core.http_client import HTTPClient

# Опциональный импорт AsyncHTTPClient (требует httpx)
try:
    from .async_client import AsyncHTTPClient
    _HAS_ASYNC = True
except ImportError:
    _HAS_ASYNC = False
    AsyncHTTPClient = None  # type: ignore
from .core.config import (
    HTTPClientConfig,
    TimeoutConfig,
    RetryConfig,
    ConnectionPoolConfig,
    SecurityConfig,
)
from .core.exceptions import (
    HTTPClientException,
    HTTPError,
    TimeoutError,
    ConnectionError,
    NotFoundError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    ServerError,
    TooManyRetriesError,
    ResponseTooLargeError,
    DecompressionBombError,
)
from .plugins.plugin import Plugin as BasePlugin
from .plugins.logging_plugin import LoggingPlugin
from .plugins.retry_plugin import RetryPlugin
from .plugins.monitoring_plugin import MonitoringPlugin
from .plugins.cache_plugin import CachePlugin
from .plugins.rate_limit_plugin import RateLimitPlugin
from .plugins.auth_plugin import AuthPlugin

# Set up logging - add NullHandler to prevent "No handler found" warnings
# Users can configure logging themselves using logging.getLogger('http_client')
logging.getLogger('http_client').addHandler(logging.NullHandler())

# Version info
__version__ = "1.0.0"
__author__ = "HTTP Client Contributors"
__license__ = "MIT"

# All public exports
__all__ = [
    # Core
    "HTTPClient",
    "AsyncHTTPClient",

    # Config
    "HTTPClientConfig",
    "TimeoutConfig",
    "RetryConfig",
    "ConnectionPoolConfig",
    "SecurityConfig",

    # Exceptions
    "HTTPClientException",
    "HTTPError",
    "TimeoutError",
    "ConnectionError",
    "NotFoundError",
    "BadRequestError",
    "UnauthorizedError",
    "ForbiddenError",
    "ServerError",
    "TooManyRetriesError",
    "ResponseTooLargeError",
    "DecompressionBombError",

    # Plugins
    "BasePlugin",
    "LoggingPlugin",
    "RetryPlugin",
    "MonitoringPlugin",
    "CachePlugin",
    "RateLimitPlugin",
    "AuthPlugin",

    # Version
    "__version__",
]
