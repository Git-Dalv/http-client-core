"""
Profile management for different environments.

Supports dev, staging, production profiles.
"""

from typing import Optional, Literal
from pathlib import Path
import os

ProfileType = Literal["development", "staging", "production"]


def get_env_file_path(profile: Optional[ProfileType] = None) -> str:
    """
    Get .env file path for profile.

    Args:
        profile: Profile name (development/staging/production)

    Returns:
        Path to .env file

    Example:
        >>> get_env_file_path("development")
        '.env.development'
        >>> get_env_file_path("production")
        '.env.production'
        >>> get_env_file_path(None)
        '.env'
    """
    if profile is None:
        # Check HTTP_CLIENT_ENV environment variable
        profile = os.getenv("HTTP_CLIENT_ENV")

    if profile is None:
        return ".env"

    return f".env.{profile}"


def detect_profile() -> Optional[ProfileType]:
    """
    Auto-detect current profile from environment.

    Checks in order:
    1. HTTP_CLIENT_ENV environment variable
    2. Common environment variables (CI, DOCKER, KUBERNETES)
    3. Returns None (use default .env)

    Returns:
        Detected profile or None

    Example:
        >>> os.environ["HTTP_CLIENT_ENV"] = "production"
        >>> detect_profile()
        'production'
    """
    # Check explicit env var
    env = os.getenv("HTTP_CLIENT_ENV")
    if env in ["development", "staging", "production"]:
        return env

    # Check common indicators
    if os.getenv("CI") == "true":
        return "staging"

    if os.getenv("KUBERNETES_SERVICE_HOST"):
        return "production"

    if os.getenv("DOCKER_CONTAINER"):
        return "production"

    # Check if running in common dev environments
    if os.getenv("VIRTUAL_ENV") or os.getenv("CONDA_DEFAULT_ENV"):
        return "development"

    return None


class ProfileConfig:
    """
    Profile-based configuration loader.

    Example:
        >>> config = ProfileConfig(profile="production")
        >>> settings = config.load()
    """

    def __init__(self, profile: Optional[ProfileType] = None):
        """
        Initialize profile config.

        Args:
            profile: Profile to use (auto-detect if None)
        """
        self.profile = profile or detect_profile()
        self.env_file = get_env_file_path(self.profile)

    def load(self) -> "HTTPClientSettings":
        """
        Load settings for this profile.

        Returns:
            HTTPClientSettings instance
        """
        from .validator import HTTPClientSettings

        # Load from profile-specific .env file
        return HTTPClientSettings(_env_file=self.env_file)

    def __repr__(self) -> str:
        """String representation."""
        return f"ProfileConfig(profile={self.profile!r}, env_file={self.env_file!r})"
