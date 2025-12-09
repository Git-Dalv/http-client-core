"""
OpenTelemetry Plugin for HTTP Client.

Provides distributed tracing support following OpenTelemetry Semantic Conventions for HTTP.
"""

import logging
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

import requests
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, Span
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.semconv.trace import SpanAttributes

from ...plugins.plugin import Plugin, PluginPriority

logger = logging.getLogger(__name__)

# Sensitive headers that should not be logged
SENSITIVE_HEADERS = {
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
    "x-csrf-token",
}


class OpenTelemetryPlugin(Plugin):
    """
    Plugin for OpenTelemetry distributed tracing.

    Priority: FIRST (0) - Must run first to properly propagate trace context.

    This plugin creates spans for each HTTP request and follows OpenTelemetry
    Semantic Conventions for HTTP spans.

    Attributes:
        - Creates spans with proper semantic attributes
        - Injects W3C Trace Context into request headers
        - Records request/response metadata
        - Handles errors and exceptions
        - Supports filtering sensitive headers

    Example:
        >>> from http_client import HTTPClient
        >>> from http_client.contrib.opentelemetry import OpenTelemetryPlugin
        >>>
        >>> client = HTTPClient(base_url="https://api.example.com")
        >>> client.add_plugin(OpenTelemetryPlugin())
        >>>
        >>> # Requests are now traced automatically
        >>> response = client.get("/users")
    """

    priority = PluginPriority.FIRST

    def __init__(
        self,
        tracer_name: str = "http_client",
        record_request_body: bool = False,
        record_response_body: bool = False,
        excluded_urls: Optional[List[str]] = None,
        capture_headers: bool = True,
        max_header_length: int = 256,
    ):
        """
        Initialize OpenTelemetry plugin.

        Args:
            tracer_name: Name of the tracer (default: "http_client")
            record_request_body: Record request body in span attributes
            record_response_body: Record response body in span attributes
            excluded_urls: List of URL patterns to exclude from tracing
            capture_headers: Whether to capture HTTP headers (sensitive headers always excluded)
            max_header_length: Maximum length for header values in attributes
        """
        self.tracer = trace.get_tracer(tracer_name)
        self.propagator = TraceContextTextMapPropagator()
        self.record_request_body = record_request_body
        self.record_response_body = record_response_body
        self.excluded_urls = set(excluded_urls) if excluded_urls else set()
        self.capture_headers = capture_headers
        self.max_header_length = max_header_length

        # Store active spans per request (thread-safe via threading.local in HTTPClient)
        self._active_spans: Dict[str, Span] = {}

    def _should_trace(self, url: str) -> bool:
        """Check if URL should be traced."""
        if not self.excluded_urls:
            return True

        for excluded in self.excluded_urls:
            if excluded in url:
                return False
        return True

    def _get_span_name(self, method: str, url: str) -> str:
        """Generate span name following semantic conventions."""
        parsed = urlparse(url)
        # Format: "HTTP {method}"
        return f"HTTP {method.upper()}"

    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Remove sensitive headers and truncate long values."""
        if not self.capture_headers:
            return {}

        sanitized = {}
        for key, value in headers.items():
            key_lower = key.lower()

            # Skip sensitive headers
            if key_lower in SENSITIVE_HEADERS:
                continue

            # Truncate long values
            if len(value) > self.max_header_length:
                value = value[: self.max_header_length] + "..."

            sanitized[key.lower()] = value

        return sanitized

    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Start span before request.

        Creates a new span and injects trace context into request headers.
        """
        # Check if should trace
        if not self._should_trace(url):
            return kwargs

        parsed_url = urlparse(url)

        # Create span
        span_name = self._get_span_name(method, url)
        span = self.tracer.start_span(span_name)

        # Set standard HTTP attributes (OpenTelemetry Semantic Conventions)
        span.set_attribute(SpanAttributes.HTTP_METHOD, method.upper())
        span.set_attribute(SpanAttributes.HTTP_URL, url)

        # URL components
        if parsed_url.scheme:
            span.set_attribute(SpanAttributes.HTTP_SCHEME, parsed_url.scheme)
        if parsed_url.hostname:
            span.set_attribute(SpanAttributes.NET_PEER_NAME, parsed_url.hostname)
        if parsed_url.port:
            span.set_attribute(SpanAttributes.NET_PEER_PORT, parsed_url.port)

        # HTTP target (path + query)
        http_target = parsed_url.path or "/"
        if parsed_url.query:
            http_target += f"?{parsed_url.query}"
        span.set_attribute(SpanAttributes.HTTP_TARGET, http_target)

        # Request headers (sanitized)
        if self.capture_headers and "headers" in kwargs:
            headers = self._sanitize_headers(kwargs.get("headers", {}))
            for key, value in headers.items():
                span.set_attribute(f"http.request.header.{key}", value)

        # Request body (if enabled)
        if self.record_request_body:
            if "json" in kwargs:
                span.set_attribute("http.request.body.json", str(kwargs["json"]))
            elif "data" in kwargs:
                span.set_attribute("http.request.body.data", str(kwargs["data"]))

        # Inject trace context into headers (W3C Trace Context)
        if "headers" not in kwargs:
            kwargs["headers"] = {}

        carrier = kwargs["headers"]
        # Create context with our span and inject trace headers
        ctx = trace.set_span_in_context(span)
        self.propagator.inject(carrier, context=ctx)

        # Store span for later use in after_response/on_error
        # Use URL as key (simple approach, could be improved with request ID)
        request_id = f"{method}:{url}"
        self._active_spans[request_id] = span

        # Store request_id in kwargs for tracking
        kwargs["_otel_request_id"] = request_id

        return kwargs

    def after_response(self, response: requests.Response) -> requests.Response:
        """
        End span after successful response.

        Adds response attributes and sets span status.
        """
        # Get request ID from response.request
        if not hasattr(response, "request"):
            return response

        request_id = getattr(response.request, "_otel_request_id", None)
        if not request_id or request_id not in self._active_spans:
            return response

        span = self._active_spans.pop(request_id)

        try:
            # Set response attributes
            span.set_attribute(SpanAttributes.HTTP_STATUS_CODE, response.status_code)

            # Response headers (sanitized)
            if self.capture_headers:
                headers = self._sanitize_headers(dict(response.headers))
                for key, value in headers.items():
                    span.set_attribute(f"http.response.header.{key}", value)

            # Response body (if enabled)
            if self.record_response_body:
                try:
                    body = response.text[:1000]  # Limit to 1000 chars
                    span.set_attribute("http.response.body", body)
                except Exception:
                    pass

            # Set span status based on HTTP status code
            if 200 <= response.status_code < 400:
                span.set_status(Status(StatusCode.OK))
            elif 400 <= response.status_code < 500:
                # Client errors - not necessarily span errors
                span.set_status(Status(StatusCode.OK))
            else:
                # Server errors
                span.set_status(
                    Status(
                        StatusCode.ERROR, f"HTTP {response.status_code}: {response.reason}"
                    )
                )

        finally:
            # Always end span
            span.end()

        return response

    def on_error(self, error: Exception, **kwargs: Any) -> bool:
        """
        Handle error and end span with error status.

        Args:
            error: Exception that occurred
            **kwargs: Additional context (method, url, etc.)

        Returns:
            False (don't retry - let retry plugin handle it)
        """
        # Try to get request ID from kwargs, or reconstruct from method/url
        request_id = kwargs.get("_otel_request_id")

        if not request_id:
            # Reconstruct request_id from method and url
            method = kwargs.get("method")
            url = kwargs.get("url")
            if method and url:
                request_id = f"{method}:{url}"

        if not request_id or request_id not in self._active_spans:
            return False

        span = self._active_spans.pop(request_id)

        try:
            # Record exception
            span.record_exception(error)

            # Set error status
            span.set_status(Status(StatusCode.ERROR, str(error)))

            # Add error attributes
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(error).__name__)
            span.set_attribute("error.message", str(error))

        finally:
            # Always end span
            span.end()

        return False  # Don't retry - let RetryPlugin handle it

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"OpenTelemetryPlugin(tracer={self.tracer}, "
            f"record_request_body={self.record_request_body}, "
            f"record_response_body={self.record_response_body})"
        )
