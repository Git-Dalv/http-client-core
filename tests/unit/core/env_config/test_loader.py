"""
Tests for configuration loader.
"""

import pytest
import os
import tempfile
from src.http_client.core.env_config.loader import load_from_env, print_config_summary
from src.http_client.core.config import HTTPClientConfig


class TestLoadFromEnv:
    """Test load_from_env function."""

    def test_load_with_defaults(self):
        """Test loading with default values."""
        config = load_from_env()
        assert isinstance(config, HTTPClientConfig)
        assert config.timeout.connect == 5
        assert config.retry.max_attempts == 3

    def test_load_from_env_file(self):
        """Test loading from .env file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as f:
            f.write("HTTP_CLIENT_BASE_URL=https://test.example.com\n")
            f.write("HTTP_CLIENT_TIMEOUT_CONNECT=15.0\n")
            env_file = f.name

        try:
            config = load_from_env(env_file=env_file)
            assert config.base_url == "https://test.example.com"
            assert config.timeout.connect == 15
        finally:
            os.remove(env_file)

    def test_load_with_overrides(self):
        """Test that overrides take priority."""
        config = load_from_env(base_url="https://override.com", timeout_connect=20.0)
        assert config.base_url == "https://override.com"
        assert config.timeout.connect == 20

    def test_load_with_profile(self):
        """Test loading with development profile."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.development') as f:
            f.write("HTTP_CLIENT_BASE_URL=http://localhost:3000\n")
            env_file = f.name

        try:
            # Need to rename to .env.development
            dev_file = ".env.development"
            with open(dev_file, 'w') as df:
                df.write("HTTP_CLIENT_BASE_URL=http://localhost:3000\n")

            config = load_from_env(profile="development")
            assert config.base_url == "http://localhost:3000"

            os.remove(dev_file)
        finally:
            if os.path.exists(env_file):
                os.remove(env_file)

    def test_logging_enabled_by_default(self):
        """Test that logging is enabled by default (console output)."""
        config = load_from_env()
        # By default, console logging is enabled
        assert config.logging is not None
        assert config.logging.enable_console is True


class TestPrintConfigSummary:
    """Test print_config_summary function."""

    def test_print_without_error(self, capsys):
        """Test that print_config_summary doesn't raise errors."""
        config = load_from_env(base_url="https://test.com")
        print_config_summary(config)

        captured = capsys.readouterr()
        assert "HTTPClientConfig" in captured.out
        assert "https://test.com" in captured.out
