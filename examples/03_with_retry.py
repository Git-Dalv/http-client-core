"""
Retry Logic Examples

Demonstrates retry mechanisms, exponential backoff, and error handling.
"""

from src.http_client import (
    HTTPClient,
    HTTPClientConfig,
    RetryConfig,
    TimeoutError,
    TooManyRetriesError,
    ServerError,
)
import time


def basic_retry():
    """Basic retry on 5xx errors."""
    print("\n=== Basic Retry ===")

    retry_cfg = RetryConfig(
        max_attempts=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504]
    )

    config = HTTPClientConfig(
        base_url="https://httpbin.org",
        retry=retry_cfg
    )

    client = HTTPClient(config=config)

    print("Requesting /status/503 (will retry 3 times)...")
    try:
        response = client.get("/status/503")
    except TooManyRetriesError as e:
        print(f"Failed after {retry_cfg.max_attempts} attempts")
        print(f"Error: {e}")


def exponential_backoff():
    """Exponential backoff demonstration."""
    print("\n=== Exponential Backoff ===")

    retry_cfg = RetryConfig(
        max_attempts=4,
        backoff_factor=2.0,  # Delays: 0s, 2s, 4s, 8s
        status_forcelist=[503]
    )

    config = HTTPClientConfig(
        base_url="https://httpbin.org",
        retry=retry_cfg
    )

    client = HTTPClient(config=config)

    print("Making request with exponential backoff...")
    print("Delays between retries: 0s -> 2s -> 4s -> 8s")

    start = time.time()
    try:
        response = client.get("/status/503")
    except TooManyRetriesError:
        elapsed = time.time() - start
        print(f"Failed after {elapsed:.1f} seconds")


def retry_on_timeout():
    """Retry on timeout errors."""
    print("\n=== Retry on Timeout ===")

    retry_cfg = RetryConfig(
        max_attempts=3,
        backoff_factor=0.3,
        status_forcelist=[408, 500, 502, 503, 504]
    )

    config = HTTPClientConfig(
        base_url="https://httpbin.org",
        timeout=1.0,  # Very short timeout
        retry=retry_cfg
    )

    client = HTTPClient(config=config)

    print("Requesting /delay/5 with 1s timeout (will timeout and retry)...")
    try:
        response = client.get("/delay/5")
    except (TimeoutError, TooManyRetriesError) as e:
        print(f"Failed: {type(e).__name__}")


def custom_retry_methods():
    """Retry only specific HTTP methods."""
    print("\n=== Custom Retry Methods ===")

    # Only retry GET and POST
    retry_cfg = RetryConfig(
        max_attempts=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503],
        allowed_methods=["GET", "POST"]  # Only these methods
    )

    config = HTTPClientConfig(
        base_url="https://httpbin.org",
        retry=retry_cfg
    )

    client = HTTPClient(config=config)

    print("GET will retry on 503:")
    try:
        response = client.get("/status/503")
    except TooManyRetriesError:
        print("  → Failed after retries")

    print("\nPUT will NOT retry (not in allowed_methods):")
    try:
        response = client.put("/status/503")
    except ServerError:
        print("  → Failed immediately (no retry)")


def retry_after_header():
    """Respect Retry-After header from server."""
    print("\n=== Retry-After Header ===")

    retry_cfg = RetryConfig(
        max_attempts=3,
        backoff_factor=1.0,
        status_forcelist=[429, 503],
        respect_retry_after=True  # Use server's Retry-After
    )

    config = HTTPClientConfig(
        base_url="https://httpbin.org",
        retry=retry_cfg
    )

    client = HTTPClient(config=config)

    print("Server may send Retry-After header...")
    print("Client will wait as instructed by server")

    try:
        # httpbin doesn't actually return Retry-After, but our client would handle it
        response = client.get("/status/429")
    except TooManyRetriesError:
        print("Failed after respecting Retry-After delays")


def no_retry():
    """Disable retry completely."""
    print("\n=== No Retry ===")

    retry_cfg = RetryConfig(
        max_attempts=1,  # No retries
        backoff_factor=0.0,
        status_forcelist=[]
    )

    config = HTTPClientConfig(
        base_url="https://httpbin.org",
        retry=retry_cfg
    )

    client = HTTPClient(config=config)

    print("Making request with no retry...")
    try:
        response = client.get("/status/503")
    except ServerError as e:
        print(f"Failed immediately: {e}")


def selective_retry():
    """Retry only specific status codes."""
    print("\n=== Selective Retry ===")

    # Only retry 503 (Service Unavailable)
    retry_cfg = RetryConfig(
        max_attempts=3,
        backoff_factor=0.5,
        status_forcelist=[503]  # Only 503
    )

    config = HTTPClientConfig(
        base_url="https://httpbin.org",
        retry=retry_cfg
    )

    client = HTTPClient(config=config)

    print("503 will retry:")
    try:
        response = client.get("/status/503")
    except TooManyRetriesError:
        print("  → Retried and failed")

    print("\n500 will NOT retry:")
    try:
        response = client.get("/status/500")
    except ServerError:
        print("  → Failed immediately")


if __name__ == "__main__":
    print("=" * 50)
    print("HTTP Client - Retry Logic Examples")
    print("=" * 50)

    try:
        basic_retry()
        exponential_backoff()
        retry_on_timeout()
        custom_retry_methods()
        retry_after_header()
        no_retry()
        selective_retry()

        print("\n" + "=" * 50)
        print("All examples completed!")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ Error: {e}")
