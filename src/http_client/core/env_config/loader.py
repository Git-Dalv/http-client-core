"""
Configuration loader from environment variables and .env files.

Main entry point for loading configuration.
"""

from typing import Optional
from pathlib import Path

from ..config import (
    HTTPClientConfig,
    TimeoutConfig,
    RetryConfig,
    SecurityConfig,
    ConnectionPoolConfig,
)
from ..logging.config import LoggingConfig
from .validator import HTTPClientSettings
from .profiles import ProfileType, ProfileConfig, get_env_file_path
from .secrets import mask_dict_secrets


def load_from_env(
    profile: Optional[ProfileType] = None,
    env_file: Optional[str] = None,
    **overrides
) -> HTTPClientConfig:
    """
    Load HTTPClientConfig from environment variables.

    Priority (highest to lowest):
    1. **overrides - explicit parameters
    2. Environment variables (HTTP_CLIENT_*)
    3. .env file (profile-specific or default)
    4. Defaults

    Args:
        profile: Profile to load (development/staging/production)
        env_file: Custom .env file path (overrides profile)
        **overrides: Explicit config overrides

    Returns:
        HTTPClientConfig instance

    Example:
        >>> # Load from .env
        >>> config = load_from_env()

        >>> # Load from production profile
        >>> config = load_from_env(profile="production")

        >>> # Load with overrides
        >>> config = load_from_env(
        ...     profile="production",
        ...     base_url="https://custom.api.com"  # Override
        ... )
    """
    # Determine env file
    if env_file is None:
        env_file = get_env_file_path(profile)

    # Load settings from environment
    settings = HTTPClientSettings(_env_file=env_file)

    # Build timeout config
    timeout = TimeoutConfig(
        connect=int(overrides.get('timeout_connect', settings.timeout_connect)),
        read=int(overrides.get('timeout_read', settings.timeout_read)),
        total=int(overrides.get('timeout_total', settings.timeout_total)) if overrides.get('timeout_total') or settings.timeout_total else None,
    )

    # Build retry config
    retry = RetryConfig(
        max_attempts=overrides.get('retry_max_attempts', settings.retry_max_attempts),
        backoff_factor=overrides.get('retry_backoff_factor', settings.retry_backoff_factor),
        backoff_jitter=overrides.get('retry_backoff_jitter', settings.retry_backoff_jitter),
        backoff_max=overrides.get('retry_backoff_max', settings.retry_backoff_max),
    )

    # Build security config
    security = SecurityConfig(
        verify_ssl=overrides.get('security_verify_ssl', settings.security_verify_ssl),
        max_response_size=overrides.get('security_max_response_size', settings.security_max_response_size),
        max_decompressed_size=overrides.get('security_max_decompressed_size', settings.security_max_decompressed_size),
    )

    # Build pool config
    pool = ConnectionPoolConfig(
        pool_connections=overrides.get('pool_connections', settings.pool_connections),
        pool_maxsize=overrides.get('pool_maxsize', settings.pool_maxsize),
        max_redirects=overrides.get('pool_max_redirects', settings.pool_max_redirects),
    )

    # Build logging config (if enabled)
    logging_config = None
    logging_settings = settings.to_logging_settings()
    if logging_settings:
        logging_config = LoggingConfig(
            level=overrides.get('log_level', logging_settings.level),
            format=overrides.get('log_format', logging_settings.format),
            enable_console=overrides.get('log_enable_console', logging_settings.enable_console),
            enable_file=overrides.get('log_enable_file', logging_settings.enable_file),
            file_path=overrides.get('log_file_path', logging_settings.file_path),
            max_bytes=overrides.get('log_max_bytes', logging_settings.max_bytes),
            backup_count=overrides.get('log_backup_count', logging_settings.backup_count),
            enable_correlation_id=overrides.get('log_enable_correlation_id', logging_settings.enable_correlation_id),
        )

    # Build final config
    config = HTTPClientConfig(
        base_url=overrides.get('base_url', settings.base_url),
        timeout=timeout,
        retry=retry,
        security=security,
        pool=pool,
        logging=logging_config,
    )

    return config


def print_config_summary(config: HTTPClientConfig, mask_secrets: bool = True):
    """
    Print configuration summary.

    Useful for debugging and verification.

    Args:
        config: Configuration to print
        mask_secrets: Mask sensitive values

    Example:
        >>> config = load_from_env()
        >>> print_config_summary(config)
        HTTPClientConfig:
          base_url: https://api.example.com
          timeout: connect=5.0s, read=10.0s, total=30.0s
          ...
    """
    print("HTTPClientConfig:")
    print(f"  base_url: {config.base_url}")
    print(f"  timeout: connect={config.timeout.connect}s, read={config.timeout.read}s, total={config.timeout.total}s")
    print(f"  retry: max_attempts={config.retry.max_attempts}, backoff={config.retry.backoff_factor}")
    print(f"  security: verify_ssl={config.security.verify_ssl}, max_size={config.security.max_response_size}")
    print(f"  pool: connections={config.pool.pool_connections}, maxsize={config.pool.pool_maxsize}")

    if config.logging:
        print(f"  logging: level={config.logging.level}, format={config.logging.format}")
        if config.logging.enable_file:
            print(f"    file: {config.logging.file_path}")
