"""
Tests for profile management.
"""

import pytest
import os
from src.http_client.core.env_config.profiles import (
    get_env_file_path,
    detect_profile,
    ProfileConfig,
)


class TestGetEnvFilePath:
    """Test get_env_file_path function."""

    def test_no_profile(self):
        """Test with no profile."""
        assert get_env_file_path(None) == ".env"

    def test_development_profile(self):
        """Test development profile."""
        assert get_env_file_path("development") == ".env.development"

    def test_staging_profile(self):
        """Test staging profile."""
        assert get_env_file_path("staging") == ".env.staging"

    def test_production_profile(self):
        """Test production profile."""
        assert get_env_file_path("production") == ".env.production"

    def test_uses_env_variable_if_profile_none(self):
        """Test that it uses HTTP_CLIENT_ENV if profile is None."""
        os.environ["HTTP_CLIENT_ENV"] = "staging"
        try:
            assert get_env_file_path(None) == ".env.staging"
        finally:
            del os.environ["HTTP_CLIENT_ENV"]


class TestDetectProfile:
    """Test detect_profile function."""

    def test_explicit_env_var_development(self):
        """Test explicit HTTP_CLIENT_ENV=development."""
        os.environ["HTTP_CLIENT_ENV"] = "development"
        try:
            assert detect_profile() == "development"
        finally:
            del os.environ["HTTP_CLIENT_ENV"]

    def test_explicit_env_var_production(self):
        """Test explicit HTTP_CLIENT_ENV=production."""
        os.environ["HTTP_CLIENT_ENV"] = "production"
        try:
            assert detect_profile() == "production"
        finally:
            del os.environ["HTTP_CLIENT_ENV"]

    def test_ci_environment(self):
        """Test CI environment detection."""
        os.environ["CI"] = "true"
        try:
            # Remove HTTP_CLIENT_ENV if set
            if "HTTP_CLIENT_ENV" in os.environ:
                del os.environ["HTTP_CLIENT_ENV"]
            assert detect_profile() == "staging"
        finally:
            if "CI" in os.environ:
                del os.environ["CI"]

    def test_kubernetes_environment(self):
        """Test Kubernetes environment detection."""
        os.environ["KUBERNETES_SERVICE_HOST"] = "10.0.0.1"
        try:
            if "HTTP_CLIENT_ENV" in os.environ:
                del os.environ["HTTP_CLIENT_ENV"]
            assert detect_profile() == "production"
        finally:
            if "KUBERNETES_SERVICE_HOST" in os.environ:
                del os.environ["KUBERNETES_SERVICE_HOST"]

    def test_virtual_env_detection(self):
        """Test virtual environment detection."""
        os.environ["VIRTUAL_ENV"] = "/path/to/venv"
        try:
            if "HTTP_CLIENT_ENV" in os.environ:
                del os.environ["HTTP_CLIENT_ENV"]
            assert detect_profile() == "development"
        finally:
            if "VIRTUAL_ENV" in os.environ:
                del os.environ["VIRTUAL_ENV"]

    def test_no_indicators(self):
        """Test with no environment indicators."""
        # Clean up all env vars
        env_vars_to_clean = ["HTTP_CLIENT_ENV", "CI", "KUBERNETES_SERVICE_HOST", "DOCKER_CONTAINER", "VIRTUAL_ENV", "CONDA_DEFAULT_ENV"]
        saved_values = {}
        for var in env_vars_to_clean:
            if var in os.environ:
                saved_values[var] = os.environ[var]
                del os.environ[var]

        try:
            assert detect_profile() is None
        finally:
            # Restore saved values
            for var, value in saved_values.items():
                os.environ[var] = value


class TestProfileConfig:
    """Test ProfileConfig class."""

    def test_init_with_explicit_profile(self):
        """Test initialization with explicit profile."""
        config = ProfileConfig(profile="production")
        assert config.profile == "production"
        assert config.env_file == ".env.production"

    def test_init_with_auto_detect(self):
        """Test initialization with auto-detect."""
        os.environ["HTTP_CLIENT_ENV"] = "staging"
        try:
            config = ProfileConfig()
            assert config.profile == "staging"
            assert config.env_file == ".env.staging"
        finally:
            del os.environ["HTTP_CLIENT_ENV"]

    def test_repr(self):
        """Test string representation."""
        config = ProfileConfig(profile="development")
        repr_str = repr(config)
        assert "ProfileConfig" in repr_str
        assert "development" in repr_str
        assert ".env.development" in repr_str
