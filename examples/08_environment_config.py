"""
Environment Configuration Examples.

Demonstrates loading configuration from .env files and environment variables.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.http_client import HTTPClient
from src.http_client.core.env_config import (
    load_from_env,
    print_config_summary,
    ProfileConfig,
    mask_secret,
    mask_dict_secrets,
)


def example_1_load_from_default_env():
    """Example 1: Load from .env file."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Load from .env")
    print("="*60 + "\n")

    # Create .env file for demo
    with open('.env', 'w') as f:
        f.write("HTTP_CLIENT_BASE_URL=https://httpbin.org\n")
        f.write("HTTP_CLIENT_LOG_LEVEL=INFO\n")
        f.write("HTTP_CLIENT_LOG_FORMAT=colored\n")

    # Load config
    config = load_from_env()

    print("Loaded configuration from .env:")
    print_config_summary(config)

    # Use config
    client = HTTPClient(config=config)
    print("\nMaking request with env config...")
    try:
        response = client.get("/get")
        print(f"Response status: {response.status_code}\n")
    except Exception as e:
        print(f"Request failed (expected in some environments): {type(e).__name__}\n")

    # Cleanup
    os.remove('.env')


def example_2_load_from_profile():
    """Example 2: Load from profile-specific .env file."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Load from Profile")
    print("="*60 + "\n")

    # Create development profile
    with open('.env.development', 'w') as f:
        f.write("HTTP_CLIENT_BASE_URL=http://localhost:8000\n")
        f.write("HTTP_CLIENT_LOG_LEVEL=DEBUG\n")
        f.write("HTTP_CLIENT_LOG_FORMAT=colored\n")
        f.write("HTTP_CLIENT_SECURITY_VERIFY_SSL=false\n")

    # Load development config
    config = load_from_env(profile="development")

    print("Loaded configuration from .env.development:")
    print_config_summary(config)
    print()

    # Cleanup
    os.remove('.env.development')


def example_3_environment_variables():
    """Example 3: Load from environment variables."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Environment Variables")
    print("="*60 + "\n")

    # Set environment variables
    os.environ["HTTP_CLIENT_BASE_URL"] = "https://httpbin.org"
    os.environ["HTTP_CLIENT_TIMEOUT_CONNECT"] = "10.0"
    os.environ["HTTP_CLIENT_LOG_LEVEL"] = "DEBUG"

    # Load config (env vars take precedence over .env file)
    config = load_from_env()

    print("Loaded configuration from environment variables:")
    print_config_summary(config)
    print()

    # Cleanup
    del os.environ["HTTP_CLIENT_BASE_URL"]
    del os.environ["HTTP_CLIENT_TIMEOUT_CONNECT"]
    del os.environ["HTTP_CLIENT_LOG_LEVEL"]


def example_4_explicit_overrides():
    """Example 4: Explicit parameter overrides."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Explicit Overrides")
    print("="*60 + "\n")

    # Create .env file
    with open('.env', 'w') as f:
        f.write("HTTP_CLIENT_BASE_URL=https://httpbin.org\n")
        f.write("HTTP_CLIENT_TIMEOUT_CONNECT=5.0\n")

    # Load config with overrides (highest priority)
    config = load_from_env(
        base_url="https://custom.api.com",  # Override
        timeout_connect=15.0,  # Override
    )

    print("Configuration with overrides:")
    print(f"  base_url: {config.base_url} (overridden)")
    print(f"  timeout.connect: {config.timeout.connect}s (overridden)")
    print()

    # Cleanup
    os.remove('.env')


def example_5_secret_masking():
    """Example 5: Secret masking for security."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Secret Masking")
    print("="*60 + "\n")

    # Example secrets
    api_key = "my-super-secret-api-key-12345"
    password = "MyP@ssw0rd123"

    print(f"Original API key: {api_key}")
    print(f"Masked API key:   {mask_secret(api_key)}\n")

    print(f"Original password: {password}")
    print(f"Masked password:   {mask_secret(password)}\n")

    # Mask dictionary
    data = {
        "username": "john_doe",
        "api_key": "secret-key-123456",
        "email": "john@example.com",
        "password": "MyPassword123",
    }

    print("Original data:")
    for k, v in data.items():
        print(f"  {k}: {v}")

    masked_data = mask_dict_secrets(data)
    print("\nMasked data:")
    for k, v in masked_data.items():
        print(f"  {k}: {v}")
    print()


def example_6_profile_auto_detection():
    """Example 6: Auto-detect profile from environment."""
    print("\n" + "="*60)
    print("EXAMPLE 6: Profile Auto-Detection")
    print("="*60 + "\n")

    # Set HTTP_CLIENT_ENV
    os.environ["HTTP_CLIENT_ENV"] = "production"

    from src.http_client.core.env_config import detect_profile

    detected = detect_profile()
    print(f"Detected profile: {detected}\n")

    # Cleanup
    del os.environ["HTTP_CLIENT_ENV"]


def example_7_complete_workflow():
    """Example 7: Complete production workflow."""
    print("\n" + "="*60)
    print("EXAMPLE 7: Complete Production Workflow")
    print("="*60 + "\n")

    # Create production .env
    with open('.env.production', 'w') as f:
        f.write("HTTP_CLIENT_BASE_URL=https://httpbin.org\n")
        f.write("HTTP_CLIENT_LOG_LEVEL=INFO\n")
        f.write("HTTP_CLIENT_LOG_FORMAT=json\n")
        f.write("HTTP_CLIENT_LOG_ENABLE_FILE=false\n")
        f.write("HTTP_CLIENT_RETRY_MAX_ATTEMPTS=3\n")
        f.write("HTTP_CLIENT_API_KEY=prod-secret-key-12345678\n")

    # Load production config
    print("Loading production configuration...")
    config = load_from_env(profile="production")

    print("\nProduction Configuration:")
    print_config_summary(config)

    # Create client
    client = HTTPClient(config=config)

    # Make request (will be logged with JSON format)
    print("\nMaking production request...")
    try:
        response = client.get("/get")
        print(f"Response: {response.status_code}\n")
    except Exception as e:
        print(f"Request failed (expected in some environments): {type(e).__name__}\n")

    # Cleanup
    os.remove('.env.production')


if __name__ == "__main__":
    example_1_load_from_default_env()
    example_2_load_from_profile()
    example_3_environment_variables()
    example_4_explicit_overrides()
    example_5_secret_masking()
    example_6_profile_auto_detection()
    example_7_complete_workflow()

    print("\n" + "="*60)
    print("All examples completed!")
    print("="*60 + "\n")
