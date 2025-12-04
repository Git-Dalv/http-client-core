"""
Environment configuration system for HTTP Client.

Load configuration from .env files and environment variables.

Example:
    >>> from src.http_client.core.env_config import load_from_env
    >>>
    >>> # Load from .env
    >>> config = load_from_env()
    >>>
    >>> # Load from production profile
    >>> config = load_from_env(profile="production")
    >>>
    >>> # Load with overrides
    >>> config = load_from_env(
    ...     profile="production",
    ...     base_url="https://custom.api.com"
    ... )
"""

from .loader import load_from_env, print_config_summary
from .validator import (
    HTTPClientSettings,
    TimeoutSettings,
    RetrySettings,
    SecuritySettings,
    PoolSettings,
    LoggingSettings,
)
from .profiles import ProfileType, ProfileConfig, detect_profile, get_env_file_path
from .secrets import mask_secret, mask_dict_secrets, is_secret_key

__all__ = [
    # Main loader
    "load_from_env",
    "print_config_summary",
    # Validators
    "HTTPClientSettings",
    "TimeoutSettings",
    "RetrySettings",
    "SecuritySettings",
    "PoolSettings",
    "LoggingSettings",
    # Profiles
    "ProfileType",
    "ProfileConfig",
    "detect_profile",
    "get_env_file_path",
    # Secrets
    "mask_secret",
    "mask_dict_secrets",
    "is_secret_key",
]
