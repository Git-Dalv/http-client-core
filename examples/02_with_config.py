"""
Advanced Configuration Examples

Demonstrates HTTPClientConfig usage with custom timeouts, retries, and security settings.
"""

from src.http_client import (
    HTTPClient,
    HTTPClientConfig,
    TimeoutConfig,
    RetryConfig,
    ConnectionPoolConfig,
    SecurityConfig,
)


def basic_config():
    """Using HTTPClientConfig.create() for simple setup."""
    print("\n=== Basic Config ===")

    config = HTTPClientConfig.create(
        base_url="https://jsonplaceholder.typicode.com",
        timeout=10
    )

    client = HTTPClient(config=config)
    response = client.get("/posts/1")

    print(f"Status: {response.status_code}")
    print(f"Config timeout: {config.timeout.total}")


def custom_timeout_config():
    """Custom timeout configuration."""
    print("\n=== Custom Timeout Config ===")

    timeout_cfg = TimeoutConfig(
        connect=5.0,    # 5 seconds to connect
        read=10.0,      # 10 seconds to read response
        total=30.0      # 30 seconds total
    )

    config = HTTPClientConfig(
        base_url="https://httpbin.org",
        timeout=timeout_cfg
    )

    client = HTTPClient(config=config)
    response = client.get("/delay/2")

    print(f"Status: {response.status_code}")
    print(f"Connect timeout: {config.timeout.connect}s")
    print(f"Read timeout: {config.timeout.read}s")


def retry_config():
    """Advanced retry configuration."""
    print("\n=== Retry Config ===")

    retry_cfg = RetryConfig(
        max_attempts=5,
        backoff_factor=1.0,
        status_forcelist=[408, 429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "DELETE"]
    )

    config = HTTPClientConfig(
        base_url="https://httpbin.org",
        retry=retry_cfg
    )

    client = HTTPClient(config=config)

    # This will retry if it fails
    try:
        response = client.get("/status/503")  # Returns 503
        print(f"Status: {response.status_code}")
    except Exception as e:
        print(f"Failed after retries: {e}")


def connection_pool_config():
    """Connection pooling configuration."""
    print("\n=== Connection Pool Config ===")

    pool_cfg = ConnectionPoolConfig(
        pool_connections=20,    # Number of connection pools
        pool_maxsize=20,        # Max connections per pool
        max_redirects=5,        # Max redirects to follow
        pool_block=False        # Don't block when pool is full
    )

    config = HTTPClientConfig(
        base_url="https://httpbin.org",
        pool=pool_cfg
    )

    client = HTTPClient(config=config)
    response = client.get("/get")

    print(f"Status: {response.status_code}")
    print(f"Pool connections: {config.pool.pool_connections}")
    print(f"Pool max size: {config.pool.pool_maxsize}")


def security_config():
    """Security configuration."""
    print("\n=== Security Config ===")

    security_cfg = SecurityConfig(
        verify_ssl=True,                    # Verify SSL certificates
        max_response_size=50 * 1024 * 1024, # 50MB max response
        allowed_hosts=["httpbin.org"]       # Only allow these hosts
    )

    config = HTTPClientConfig(
        base_url="https://httpbin.org",
        security=security_cfg
    )

    client = HTTPClient(config=config)
    response = client.get("/get")

    print(f"Status: {response.status_code}")
    print(f"SSL verified: {config.security.verify_ssl}")
    print(f"Max response size: {config.security.max_response_size} bytes")


def full_config():
    """Complete configuration with all options."""
    print("\n=== Full Config ===")

    config = HTTPClientConfig(
        base_url="https://jsonplaceholder.typicode.com",
        headers={"User-Agent": "MyApp/1.0"},

        timeout=TimeoutConfig(
            connect=3.0,
            read=10.0,
            total=30.0
        ),

        retry=RetryConfig(
            max_attempts=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        ),

        pool=ConnectionPoolConfig(
            pool_connections=10,
            pool_maxsize=10,
            max_redirects=3,
            pool_block=False
        ),

        security=SecurityConfig(
            verify_ssl=True,
            max_response_size=100 * 1024 * 1024,  # 100MB
            allowed_hosts=None  # Allow all hosts
        )
    )

    client = HTTPClient(config=config)
    response = client.get("/posts/1")

    print(f"Status: {response.status_code}")
    print(f"User-Agent: {config.headers['User-Agent']}")
    print(f"Max retries: {config.retry.max_attempts}")
    print(f"Timeout: {config.timeout.total}s")


def immutable_config():
    """Configuration is immutable."""
    print("\n=== Immutable Config ===")

    config = HTTPClientConfig.create(
        base_url="https://jsonplaceholder.typicode.com",
        timeout=10
    )

    print(f"Original timeout: {config.timeout.total}s")

    # Try to modify (will fail)
    try:
        config.timeout = TimeoutConfig(total=20.0)
        print("Config modified (should not happen!)")
    except Exception as e:
        print(f"Cannot modify: {type(e).__name__}")

    # To change config, create new one
    new_config = config.replace(
        timeout=TimeoutConfig(total=20.0)
    )

    print(f"New config timeout: {new_config.timeout.total}s")
    print(f"Original unchanged: {config.timeout.total}s")


if __name__ == "__main__":
    print("=" * 50)
    print("HTTP Client - Advanced Configuration")
    print("=" * 50)

    try:
        basic_config()
        custom_timeout_config()
        retry_config()
        connection_pool_config()
        security_config()
        full_config()
        immutable_config()

        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ Error: {e}")
