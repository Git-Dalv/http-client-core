"""
OpenTelemetry integration for http-client-core.

This module provides OpenTelemetry tracing and metrics support for HTTP requests.
Requires opentelemetry-api and opentelemetry-sdk to be installed.

Installation:
    pip install http-client-core[otel]

Example:
    >>> from http_client import HTTPClient
    >>> from http_client.contrib.opentelemetry import OpenTelemetryPlugin
    >>>
    >>> from opentelemetry import trace
    >>> from opentelemetry.sdk.trace import TracerProvider
    >>> from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
    >>>
    >>> # Setup tracer
    >>> provider = TracerProvider()
    >>> provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    >>> trace.set_tracer_provider(provider)
    >>>
    >>> # Use plugin
    >>> client = HTTPClient(base_url="https://api.example.com")
    >>> client.add_plugin(OpenTelemetryPlugin())
    >>> response = client.get("/users")  # Traced automatically
"""

# Check if OpenTelemetry is installed
try:
    import opentelemetry  # noqa: F401
except ImportError as e:
    raise ImportError(
        "OpenTelemetry support requires opentelemetry-api and opentelemetry-sdk. "
        "Install with: pip install http-client-core[otel]"
    ) from e

from .plugin import OpenTelemetryPlugin
from .metrics import OpenTelemetryMetrics

__all__ = [
    "OpenTelemetryPlugin",
    "OpenTelemetryMetrics",
]
