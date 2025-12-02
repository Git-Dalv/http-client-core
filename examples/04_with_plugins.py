"""
Plugin System Examples

Demonstrates how to use and create custom plugins for logging, monitoring, caching, etc.
"""

from src.http_client import (
    HTTPClient,
    HTTPClientConfig,
    LoggingPlugin,
    MonitoringPlugin,
    CachePlugin,
    RateLimitPlugin,
    AuthPlugin,
)
from src.http_client.plugins.plugin import Plugin
import logging
from typing import Any, Dict
import requests


# Configure logging to see plugin output
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def with_logging_plugin():
    """Using LoggingPlugin for request/response logging."""
    print("\n=== Logging Plugin ===")

    config = HTTPClientConfig.create(
        base_url="https://jsonplaceholder.typicode.com"
    )

    # Add logging plugin
    log_plugin = LoggingPlugin(level=logging.INFO)

    client = HTTPClient(config=config)
    client.register_plugin(log_plugin)

    print("Making request (check logs)...")
    response = client.get("/posts/1")
    print(f"Status: {response.status_code}")


def with_monitoring_plugin():
    """Using MonitoringPlugin to track metrics."""
    print("\n=== Monitoring Plugin ===")

    config = HTTPClientConfig.create(
        base_url="https://jsonplaceholder.typicode.com"
    )

    # Add monitoring plugin
    monitor = MonitoringPlugin()

    client = HTTPClient(config=config)
    client.register_plugin(monitor)

    # Make several requests
    client.get("/posts/1")
    client.get("/posts/2")
    client.get("/posts/3")

    # Get metrics
    metrics = monitor.get_metrics()
    print(f"Total requests: {metrics['total_requests']}")
    print(f"Successful: {metrics['successful_requests']}")
    print(f"Failed: {metrics['failed_requests']}")
    print(f"Average time: {metrics['average_response_time']:.3f}s")


def with_cache_plugin():
    """Using CachePlugin for response caching."""
    print("\n=== Cache Plugin ===")

    config = HTTPClientConfig.create(
        base_url="https://jsonplaceholder.typicode.com"
    )

    # Add cache plugin (TTL = 60 seconds)
    cache = CachePlugin(ttl=60, max_size=100)

    client = HTTPClient(config=config)
    client.register_plugin(cache)

    print("First request (will be cached):")
    response1 = client.get("/posts/1")
    print(f"  Status: {response1.status_code}")

    print("\nSecond request (from cache):")
    response2 = client.get("/posts/1")
    print(f"  Status: {response2.status_code}")
    print(f"  Same data: {response1.json() == response2.json()}")

    # Check cache stats
    print(f"\nCache hits: {cache.hits}")
    print(f"Cache misses: {cache.misses}")


def with_rate_limit_plugin():
    """Using RateLimitPlugin to limit request rate."""
    print("\n=== Rate Limit Plugin ===")

    config = HTTPClientConfig.create(
        base_url="https://jsonplaceholder.typicode.com"
    )

    # Limit to 2 requests per second
    rate_limiter = RateLimitPlugin(max_calls=2, period=1.0)

    client = HTTPClient(config=config)
    client.register_plugin(rate_limiter)

    print("Making 5 requests (limited to 2/sec)...")
    import time
    start = time.time()

    for i in range(5):
        response = client.get(f"/posts/{i+1}")
        elapsed = time.time() - start
        print(f"  Request {i+1}: {response.status_code} at {elapsed:.2f}s")

    total_time = time.time() - start
    print(f"\nTotal time: {total_time:.2f}s (rate-limited)")


def with_auth_plugin():
    """Using AuthPlugin for authentication."""
    print("\n=== Auth Plugin ===")

    config = HTTPClientConfig.create(
        base_url="https://httpbin.org"
    )

    # Add bearer token auth
    auth = AuthPlugin(auth_type="bearer", token="my-secret-token-123")

    client = HTTPClient(config=config)
    client.register_plugin(auth)

    print("Making authenticated request...")
    response = client.get("/bearer")

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Token received by server: {data.get('token', 'N/A')}")


def multiple_plugins():
    """Using multiple plugins together."""
    print("\n=== Multiple Plugins ===")

    config = HTTPClientConfig.create(
        base_url="https://jsonplaceholder.typicode.com"
    )

    # Register multiple plugins
    log_plugin = LoggingPlugin(level=logging.INFO)
    monitor = MonitoringPlugin()
    cache = CachePlugin(ttl=30)

    client = HTTPClient(config=config)
    client.register_plugin(log_plugin)
    client.register_plugin(monitor)
    client.register_plugin(cache)

    print("Making requests with logging, monitoring, and caching...")

    # First request - cache miss
    response1 = client.get("/posts/1")
    print(f"First request: {response1.status_code}")

    # Second request - cache hit
    response2 = client.get("/posts/1")
    print(f"Second request: {response2.status_code} (cached)")

    # Get metrics
    metrics = monitor.get_metrics()
    print(f"\nMetrics: {metrics['total_requests']} requests")
    print(f"Cache: {cache.hits} hits, {cache.misses} misses")


class CustomHeaderPlugin(Plugin):
    """Custom plugin that adds headers to every request."""

    def __init__(self, custom_header: str, value: str):
        super().__init__()
        self.custom_header = custom_header
        self.value = value

    def before_request(self, request_info: Dict[str, Any]) -> Dict[str, Any]:
        """Add custom header before request."""
        if 'headers' not in request_info:
            request_info['headers'] = {}

        request_info['headers'][self.custom_header] = self.value
        print(f"  → Added header: {self.custom_header}={self.value}")

        return request_info

    def after_response(self, response: requests.Response,
                       request_info: Dict[str, Any]) -> requests.Response:
        """Log response after receiving."""
        print(f"  → Response: {response.status_code}")
        return response


def custom_plugin():
    """Creating and using a custom plugin."""
    print("\n=== Custom Plugin ===")

    config = HTTPClientConfig.create(
        base_url="https://httpbin.org"
    )

    # Create custom plugin
    custom = CustomHeaderPlugin(
        custom_header="X-My-App",
        value="CustomPluginDemo/1.0"
    )

    client = HTTPClient(config=config)
    client.register_plugin(custom)

    print("Making request with custom plugin...")
    response = client.get("/headers")

    # Check if our header was sent
    if response.status_code == 200:
        headers = response.json()['headers']
        print(f"\nHeaders sent to server:")
        print(f"  X-My-App: {headers.get('X-My-App', 'NOT FOUND')}")


if __name__ == "__main__":
    print("=" * 50)
    print("HTTP Client - Plugin System Examples")
    print("=" * 50)

    try:
        with_logging_plugin()
        with_monitoring_plugin()
        with_cache_plugin()
        with_rate_limit_plugin()
        with_auth_plugin()
        multiple_plugins()
        custom_plugin()

        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ Error: {e}")
