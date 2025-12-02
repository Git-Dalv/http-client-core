"""
Advanced Logging Examples for HTTP Client Core.

Demonstrates the new logging system with different formats,
correlation IDs, file logging, and production setup.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.http_client import HTTPClient
from src.http_client.core.config import HTTPClientConfig
from src.http_client.core.logging import LoggingConfig


def example_1_basic_logging():
    """Example 1: Basic logging with colored console output."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Logging (Colored Console)")
    print("="*60 + "\n")

    # Create logging config
    logging_config = LoggingConfig.create(
        level="INFO",
        format="colored",
        enable_console=True,
        enable_file=False
    )

    # Create HTTP client config with logging
    config = HTTPClientConfig.create(
        base_url="https://httpbin.org",
        logging=logging_config
    )

    # Create client
    client = HTTPClient(config=config)

    # Make some requests
    print("Making GET request...")
    response = client.get("/get")
    print(f"Response: {response.status_code}\n")

    print("Making POST request...")
    response = client.post("/post", json={"key": "value"})
    print(f"Response: {response.status_code}\n")


def example_2_json_logging():
    """Example 2: JSON logging for production."""
    print("\n" + "="*60)
    print("EXAMPLE 2: JSON Logging (Production)")
    print("="*60 + "\n")

    logging_config = LoggingConfig.create(
        level="INFO",
        format="json",
        enable_console=True,
        enable_file=False,
        enable_correlation_id=True
    )

    config = HTTPClientConfig.create(
        base_url="https://httpbin.org",
        logging=logging_config
    )

    client = HTTPClient(config=config)

    # Each request will have correlation ID
    print("Making requests with correlation IDs...\n")
    response = client.get("/get")
    response = client.post("/post", json={"test": "data"})
    print()


def example_3_file_logging():
    """Example 3: File logging with rotation."""
    print("\n" + "="*60)
    print("EXAMPLE 3: File Logging with Rotation")
    print("="*60 + "\n")

    log_file = "/tmp/http_client_example.log"

    logging_config = LoggingConfig.create(
        level="DEBUG",
        format="json",
        enable_console=True,
        enable_file=True,
        file_path=log_file,
        max_bytes=1024 * 1024,  # 1MB
        backup_count=3
    )

    config = HTTPClientConfig.create(
        base_url="https://httpbin.org",
        logging=logging_config
    )

    client = HTTPClient(config=config)

    print(f"Logging to file: {log_file}\n")

    # Make requests
    response = client.get("/get")
    response = client.post("/post", json={"file": "logging"})

    # Show log file contents
    print(f"\nLog file contents ({log_file}):")
    print("-" * 60)
    with open(log_file, 'r') as f:
        print(f.read())
    print("-" * 60 + "\n")


def example_4_retry_logging():
    """Example 4: Logging with retry attempts."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Retry Logging")
    print("="*60 + "\n")

    from src.http_client.core.config import RetryConfig

    logging_config = LoggingConfig.create(
        level="INFO",
        format="colored",
        enable_console=True
    )

    retry_config = RetryConfig(
        max_attempts=3,
        backoff_factor=1.0,
        backoff_jitter=True
    )

    config = HTTPClientConfig.create(
        base_url="https://httpbin.org",
        logging=logging_config,
        retry=retry_config
    )

    client = HTTPClient(config=config)

    print("Making request that will trigger retries (status 500)...\n")
    try:
        # This will fail and retry
        response = client.get("/status/500")
    except Exception as e:
        print(f"\nExpected error after retries: {e}\n")


def example_5_production_setup():
    """Example 5: Production-ready setup."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Production Setup")
    print("="*60 + "\n")

    from src.http_client.core.config import TimeoutConfig, SecurityConfig, RetryConfig

    # Production logging config
    logging_config = LoggingConfig.create(
        level="INFO",
        format="json",
        enable_console=True,
        enable_file=True,
        file_path="/tmp/http_client_prod.log",
        max_bytes=10 * 1024 * 1024,  # 10MB
        backup_count=5,
        enable_correlation_id=True,
        extra_fields={
            "environment": "production",
            "version": "1.0.0",
            "service": "api-client"
        }
    )

    # Full config
    config = HTTPClientConfig.create(
        base_url="https://httpbin.org",
        timeout=TimeoutConfig(connect=5, read=10, total=30),
        retry=RetryConfig(max_attempts=3, backoff_factor=2.0),
        security=SecurityConfig(
            verify_ssl=True,
            max_response_size=10 * 1024 * 1024
        ),
        logging=logging_config
    )

    client = HTTPClient(config=config)

    print("Production setup:")
    print(f"  - JSON logging: ✓")
    print(f"  - File logging: ✓ (/tmp/http_client_prod.log)")
    print(f"  - Correlation ID: ✓")
    print(f"  - Retry: ✓ (3 attempts)")
    print(f"  - Timeouts: ✓ (connect=5s, read=10s, total=30s)")
    print(f"  - Security: ✓ (SSL verify, size limits)\n")

    # Make request
    print("Making production request...\n")
    response = client.get("/get")
    print(f"Response: {response.status_code}\n")

    # Show structured log
    print("Structured log sample:")
    print("-" * 60)
    with open("/tmp/http_client_prod.log", 'r') as f:
        lines = f.readlines()
        if lines:
            import json
            log_entry = json.loads(lines[-1])
            print(json.dumps(log_entry, indent=2))
    print("-" * 60 + "\n")


def example_6_no_logging():
    """Example 6: Disable logging (default behavior)."""
    print("\n" + "="*60)
    print("EXAMPLE 6: No Logging (Default)")
    print("="*60 + "\n")

    # No logging config = no logging
    config = HTTPClientConfig.create(
        base_url="https://httpbin.org"
    )

    client = HTTPClient(config=config)

    print("Making request without logging...\n")
    response = client.get("/get")
    print(f"Response: {response.status_code}")
    print("(No logs printed - logging disabled)\n")


if __name__ == "__main__":
    # Run all examples
    example_1_basic_logging()
    example_2_json_logging()
    example_3_file_logging()
    example_4_retry_logging()
    example_5_production_setup()
    example_6_no_logging()

    print("\n" + "="*60)
    print("All examples completed!")
    print("="*60 + "\n")
