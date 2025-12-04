"""Core HTTP Client модули."""

from .config import (
    TimeoutConfig,
    RetryConfig,
    ConnectionPoolConfig,
    SecurityConfig,
    HTTPClientConfig,
)
from .retry_engine import RetryEngine
from .exceptions import (
    HTTPClientException,
    TemporaryError,
    FatalError,
    NetworkError,
    TimeoutError,
    ConnectionError,
    ProxyError,
    DNSError,
    ServerError,
    TooManyRequestsError,
    HTTPError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    InvalidResponseError,
    ResponseTooLargeError,
    DecompressionBombError,
    TooManyRetriesError,
    ConfigurationError,
    classify_requests_exception,
)
from .http_client import HTTPClient, get_current_request_context
from .error_handler import ErrorHandler
from .context import RequestContext

__all__ = [
    # Config
    "TimeoutConfig",
    "RetryConfig",
    "ConnectionPoolConfig",
    "SecurityConfig",
    "HTTPClientConfig",
    # Retry
    "RetryEngine",
    # Core
    "HTTPClient",
    "ErrorHandler",
    "get_current_request_context",
    "RequestContext",
    # Exceptions
    "HTTPClientException",
    "TemporaryError",
    "FatalError",
    "NetworkError",
    "TimeoutError",
    "ConnectionError",
    "ProxyError",
    "DNSError",
    "ServerError",
    "TooManyRequestsError",
    "HTTPError",
    "BadRequestError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "InvalidResponseError",
    "ResponseTooLargeError",
    "DecompressionBombError",
    "TooManyRetriesError",
    "ConfigurationError",
    "classify_requests_exception",
]
