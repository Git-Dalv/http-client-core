"""
OpenTelemetry Metrics for HTTP Client.

Provides metrics collection following OpenTelemetry Semantic Conventions.
"""

import logging
import time
from typing import Any, Dict
from urllib.parse import urlparse

import requests
from opentelemetry import metrics
from opentelemetry.metrics import Counter, Histogram, UpDownCounter

from ...plugins.plugin import Plugin, PluginPriority

logger = logging.getLogger(__name__)


class OpenTelemetryMetrics(Plugin):
    """
    Plugin for OpenTelemetry metrics collection.

    Priority: LAST (100) - Should run last to capture accurate metrics.

    Collects the following metrics:
    - http_client_requests_total: Total number of HTTP requests (Counter)
    - http_client_request_duration_seconds: HTTP request duration (Histogram)
    - http_client_active_requests: Number of active HTTP requests (UpDownCounter)

    All metrics include labels:
    - method: HTTP method (GET, POST, etc.)
    - status: HTTP status code (200, 404, etc.) or "error"
    - host: Target host

    Example:
        >>> from http_client import HTTPClient
        >>> from http_client.contrib.opentelemetry import OpenTelemetryMetrics
        >>>
        >>> from opentelemetry import metrics
        >>> from opentelemetry.sdk.metrics import MeterProvider
        >>> from opentelemetry.sdk.metrics.export import (
        ...     ConsoleMetricExporter,
        ...     PeriodicExportingMetricReader,
        ... )
        >>>
        >>> # Setup meter
        >>> reader = PeriodicExportingMetricReader(ConsoleMetricExporter())
        >>> provider = MeterProvider(metric_readers=[reader])
        >>> metrics.set_meter_provider(provider)
        >>>
        >>> # Use plugin
        >>> client = HTTPClient(base_url="https://api.example.com")
        >>> client.add_plugin(OpenTelemetryMetrics())
        >>> response = client.get("/users")  # Metrics collected automatically
    """

    priority = PluginPriority.LAST

    def __init__(self, meter_name: str = "http_client"):
        """
        Initialize OpenTelemetry metrics plugin.

        Args:
            meter_name: Name of the meter (default: "http_client")
        """
        self.meter = metrics.get_meter(meter_name)

        # Create metrics
        self.request_counter: Counter = self.meter.create_counter(
            name="http_client_requests_total",
            description="Total number of HTTP requests",
            unit="requests",
        )

        self.request_duration: Histogram = self.meter.create_histogram(
            name="http_client_request_duration_seconds",
            description="HTTP request duration in seconds",
            unit="s",
        )

        self.active_requests: UpDownCounter = self.meter.create_up_down_counter(
            name="http_client_active_requests",
            description="Number of active HTTP requests",
            unit="requests",
        )

        # Store start times per request
        self._start_times: Dict[str, float] = {}

    def _get_labels(
        self, method: str, url: str, status_code: int = None, error: bool = False
    ) -> Dict[str, str]:
        """
        Generate metric labels.

        Args:
            method: HTTP method
            url: Request URL
            status_code: HTTP status code (optional)
            error: Whether request errored

        Returns:
            Dictionary of labels
        """
        parsed_url = urlparse(url)

        labels = {
            "method": method.upper(),
            "host": parsed_url.hostname or "unknown",
        }

        if status_code is not None:
            labels["status"] = str(status_code)
        elif error:
            labels["status"] = "error"

        return labels

    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Record request start.

        Increments active requests counter and records start time.
        """
        # Increment active requests
        labels = self._get_labels(method, url)
        self.active_requests.add(1, labels)

        # Record start time
        request_id = f"{method}:{url}"
        self._start_times[request_id] = time.time()

        # Store request_id in kwargs for tracking
        kwargs["_metrics_request_id"] = request_id

        return kwargs

    def after_response(self, response: requests.Response) -> requests.Response:
        """
        Record metrics after successful response.

        Decrements active requests, increments request counter,
        and records duration.
        """
        # Get request ID from response.request
        if not hasattr(response, "request"):
            return response

        request_id = getattr(response.request, "_metrics_request_id", None)
        if not request_id:
            return response

        # Get method and URL from request
        method = response.request.method
        url = str(response.request.url)

        # Calculate duration
        start_time = self._start_times.pop(request_id, None)
        if start_time:
            duration = time.time() - start_time
        else:
            duration = 0.0

        # Get labels
        labels = self._get_labels(method, url, status_code=response.status_code)

        # Decrement active requests
        self.active_requests.add(-1, labels)

        # Increment request counter
        self.request_counter.add(1, labels)

        # Record duration
        self.request_duration.record(duration, labels)

        return response

    def on_error(self, error: Exception, **kwargs: Any) -> bool:
        """
        Record metrics on error.

        Decrements active requests, increments error counter,
        and records duration.

        Args:
            error: Exception that occurred
            **kwargs: Additional context (method, url, etc.)

        Returns:
            False (don't retry - let retry plugin handle it)
        """
        # Get request ID from kwargs
        request_id = kwargs.get("_metrics_request_id")
        if not request_id:
            return False

        # Get method and URL
        method = kwargs.get("method", "UNKNOWN")
        url = kwargs.get("url", "unknown")

        # Calculate duration
        start_time = self._start_times.pop(request_id, None)
        if start_time:
            duration = time.time() - start_time
        else:
            duration = 0.0

        # Get labels with error status
        labels = self._get_labels(method, url, error=True)

        # Decrement active requests
        self.active_requests.add(-1, labels)

        # Increment request counter
        self.request_counter.add(1, labels)

        # Record duration
        self.request_duration.record(duration, labels)

        return False  # Don't retry - let RetryPlugin handle it

    def __repr__(self) -> str:
        """String representation."""
        return f"OpenTelemetryMetrics(meter={self.meter})"
