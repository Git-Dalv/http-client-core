"""Tests for configuration file loader."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.http_client.core.env_config.file_loader import (
    ConfigFileLoader,
    ConfigValidationError,
)
from src.http_client.core.config import HTTPClientConfig


class TestFromYAML:
    """Test loading from YAML files."""

    def test_load_valid_yaml(self, tmp_path):
        """Test loading valid YAML config."""
        pytest.importorskip("yaml")

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
http_client:
  base_url: "https://api.example.com"
  timeout:
    connect: 10
    read: 60
  retry:
    max_attempts: 5
  security:
    verify_ssl: true
  headers:
    User-Agent: "TestApp/1.0"
"""
        )

        config = ConfigFileLoader.from_yaml(config_file)

        assert isinstance(config, HTTPClientConfig)
        assert config.base_url == "https://api.example.com"
        assert config.timeout.connect == 10
        assert config.timeout.read == 60
        assert config.retry.max_attempts == 5
        assert config.security.verify_ssl is True
        assert config.headers["User-Agent"] == "TestApp/1.0"

    def test_load_minimal_yaml(self, tmp_path):
        """Test loading minimal YAML config."""
        pytest.importorskip("yaml")

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
http_client:
  base_url: "https://api.example.com"
"""
        )

        config = ConfigFileLoader.from_yaml(config_file)

        assert isinstance(config, HTTPClientConfig)
        assert config.base_url == "https://api.example.com"
        # Should have defaults
        assert config.timeout.connect == 5
        assert config.retry.max_attempts == 3

    def test_load_yaml_without_http_client_section(self, tmp_path):
        """Test loading YAML without http_client wrapper."""
        pytest.importorskip("yaml")

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
base_url: "https://api.example.com"
timeout:
  connect: 15
  read: 45
"""
        )

        config = ConfigFileLoader.from_yaml(config_file)

        assert isinstance(config, HTTPClientConfig)
        assert config.base_url == "https://api.example.com"
        assert config.timeout.connect == 15
        assert config.timeout.read == 45

    def test_load_yaml_with_logging(self, tmp_path):
        """Test loading YAML with logging config."""
        pytest.importorskip("yaml")

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
http_client:
  base_url: "https://api.example.com"
  logging:
    level: "DEBUG"
    format: "json"
    enable_console: true
"""
        )

        config = ConfigFileLoader.from_yaml(config_file)

        assert config.logging is not None
        assert config.logging.level == "DEBUG"
        assert config.logging.format == "json"
        assert config.logging.enable_console is True

    def test_load_yaml_with_circuit_breaker(self, tmp_path):
        """Test loading YAML with circuit breaker config."""
        pytest.importorskip("yaml")

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
http_client:
  base_url: "https://api.example.com"
  circuit_breaker:
    enabled: true
    failure_threshold: 10
    recovery_timeout: 60.0
"""
        )

        config = ConfigFileLoader.from_yaml(config_file)

        assert config.circuit_breaker.enabled is True
        assert config.circuit_breaker.failure_threshold == 10
        assert config.circuit_breaker.recovery_timeout == 60.0

    def test_yaml_file_not_found(self, tmp_path):
        """Test error when YAML file doesn't exist."""
        pytest.importorskip("yaml")

        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError, match="Config file not found"):
            ConfigFileLoader.from_yaml(config_file)

    def test_yaml_invalid_syntax(self, tmp_path):
        """Test error with invalid YAML syntax."""
        pytest.importorskip("yaml")

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
http_client:
  base_url: "https://api.example.com
  # Missing closing quote
"""
        )

        with pytest.raises(ConfigValidationError, match="Invalid YAML syntax"):
            ConfigFileLoader.from_yaml(config_file)

    def test_yaml_empty_file(self, tmp_path):
        """Test error with empty YAML file."""
        pytest.importorskip("yaml")

        config_file = tmp_path / "config.yaml"
        config_file.write_text("")

        with pytest.raises(ConfigValidationError, match="Empty config file"):
            ConfigFileLoader.from_yaml(config_file)

    def test_yaml_without_pyyaml(self, tmp_path, monkeypatch):
        """Test error when PyYAML is not installed."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("http_client:\n  base_url: test")

        # Mock import error
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("No module named 'yaml'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        with pytest.raises(ImportError, match="PyYAML is required"):
            ConfigFileLoader.from_yaml(config_file)


class TestFromJSON:
    """Test loading from JSON files."""

    def test_load_valid_json(self, tmp_path):
        """Test loading valid JSON config."""
        config_file = tmp_path / "config.json"
        config_data = {
            "http_client": {
                "base_url": "https://api.example.com",
                "timeout": {"connect": 10, "read": 60},
                "retry": {"max_attempts": 5},
                "security": {"verify_ssl": True},
                "headers": {"User-Agent": "TestApp/1.0"},
            }
        }
        config_file.write_text(json.dumps(config_data))

        config = ConfigFileLoader.from_json(config_file)

        assert isinstance(config, HTTPClientConfig)
        assert config.base_url == "https://api.example.com"
        assert config.timeout.connect == 10
        assert config.timeout.read == 60
        assert config.retry.max_attempts == 5
        assert config.security.verify_ssl is True
        assert config.headers["User-Agent"] == "TestApp/1.0"

    def test_load_minimal_json(self, tmp_path):
        """Test loading minimal JSON config."""
        config_file = tmp_path / "config.json"
        config_data = {"http_client": {"base_url": "https://api.example.com"}}
        config_file.write_text(json.dumps(config_data))

        config = ConfigFileLoader.from_json(config_file)

        assert isinstance(config, HTTPClientConfig)
        assert config.base_url == "https://api.example.com"
        # Should have defaults
        assert config.timeout.connect == 5
        assert config.retry.max_attempts == 3

    def test_load_json_with_retry_on_status(self, tmp_path):
        """Test loading JSON with retry_on_status."""
        config_file = tmp_path / "config.json"
        config_data = {
            "http_client": {
                "base_url": "https://api.example.com",
                "retry": {"max_attempts": 3, "retry_on_status": [500, 502, 503]},
            }
        }
        config_file.write_text(json.dumps(config_data))

        config = ConfigFileLoader.from_json(config_file)

        assert config.retry.max_attempts == 3
        assert 500 in config.retry.retryable_status_codes
        assert 502 in config.retry.retryable_status_codes
        assert 503 in config.retry.retryable_status_codes

    def test_json_file_not_found(self, tmp_path):
        """Test error when JSON file doesn't exist."""
        config_file = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError, match="Config file not found"):
            ConfigFileLoader.from_json(config_file)

    def test_json_invalid_syntax(self, tmp_path):
        """Test error with invalid JSON syntax."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"http_client": {"base_url": }')  # Invalid JSON

        with pytest.raises(ConfigValidationError, match="Invalid JSON syntax"):
            ConfigFileLoader.from_json(config_file)

    def test_json_empty_file(self, tmp_path):
        """Test error with empty JSON file."""
        config_file = tmp_path / "config.json"
        config_file.write_text("")

        with pytest.raises(ConfigValidationError, match="Invalid JSON syntax"):
            ConfigFileLoader.from_json(config_file)


class TestFromFile:
    """Test auto-detection by file extension."""

    def test_auto_detect_yaml(self, tmp_path):
        """Test auto-detection of YAML file."""
        pytest.importorskip("yaml")

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
http_client:
  base_url: "https://api.example.com"
"""
        )

        config = ConfigFileLoader.from_file(config_file)

        assert isinstance(config, HTTPClientConfig)
        assert config.base_url == "https://api.example.com"

    def test_auto_detect_yml(self, tmp_path):
        """Test auto-detection of .yml file."""
        pytest.importorskip("yaml")

        config_file = tmp_path / "config.yml"
        config_file.write_text(
            """
http_client:
  base_url: "https://api.example.com"
"""
        )

        config = ConfigFileLoader.from_file(config_file)

        assert isinstance(config, HTTPClientConfig)
        assert config.base_url == "https://api.example.com"

    def test_auto_detect_json(self, tmp_path):
        """Test auto-detection of JSON file."""
        config_file = tmp_path / "config.json"
        config_data = {"http_client": {"base_url": "https://api.example.com"}}
        config_file.write_text(json.dumps(config_data))

        config = ConfigFileLoader.from_file(config_file)

        assert isinstance(config, HTTPClientConfig)
        assert config.base_url == "https://api.example.com"

    def test_unsupported_format(self, tmp_path):
        """Test error with unsupported file format."""
        config_file = tmp_path / "config.txt"
        config_file.write_text("base_url: https://api.example.com")

        with pytest.raises(ValueError, match="Unsupported config file format"):
            ConfigFileLoader.from_file(config_file)


class TestFromEnvPath:
    """Test loading from environment variable."""

    def test_load_from_env_var_yaml(self, tmp_path, monkeypatch):
        """Test loading from HTTP_CLIENT_CONFIG_FILE env var (YAML)."""
        pytest.importorskip("yaml")

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
http_client:
  base_url: "https://api.example.com"
  timeout:
    connect: 20
"""
        )

        monkeypatch.setenv("HTTP_CLIENT_CONFIG_FILE", str(config_file))

        config = ConfigFileLoader.from_env_path()

        assert config is not None
        assert isinstance(config, HTTPClientConfig)
        assert config.base_url == "https://api.example.com"
        assert config.timeout.connect == 20

    def test_load_from_env_var_json(self, tmp_path, monkeypatch):
        """Test loading from HTTP_CLIENT_CONFIG_FILE env var (JSON)."""
        config_file = tmp_path / "config.json"
        config_data = {"http_client": {"base_url": "https://api.example.com"}}
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setenv("HTTP_CLIENT_CONFIG_FILE", str(config_file))

        config = ConfigFileLoader.from_env_path()

        assert config is not None
        assert isinstance(config, HTTPClientConfig)
        assert config.base_url == "https://api.example.com"

    def test_env_var_not_set(self, monkeypatch):
        """Test returns None when env var is not set."""
        monkeypatch.delenv("HTTP_CLIENT_CONFIG_FILE", raising=False)

        config = ConfigFileLoader.from_env_path()

        assert config is None


class TestConfigValidation:
    """Test configuration validation."""

    def test_invalid_timeout_type(self, tmp_path):
        """Test error with invalid timeout type."""
        config_file = tmp_path / "config.json"
        config_data = {"http_client": {"timeout": "invalid"}}  # Should be dict
        config_file.write_text(json.dumps(config_data))

        with pytest.raises(ConfigValidationError, match="timeout must be a dictionary"):
            ConfigFileLoader.from_json(config_file)

    def test_invalid_retry_type(self, tmp_path):
        """Test error with invalid retry type."""
        config_file = tmp_path / "config.json"
        config_data = {"http_client": {"retry": "invalid"}}  # Should be dict
        config_file.write_text(json.dumps(config_data))

        with pytest.raises(ConfigValidationError, match="retry must be a dictionary"):
            ConfigFileLoader.from_json(config_file)

    def test_invalid_headers_type(self, tmp_path):
        """Test error with invalid headers type."""
        config_file = tmp_path / "config.json"
        config_data = {"http_client": {"headers": "invalid"}}  # Should be dict
        config_file.write_text(json.dumps(config_data))

        with pytest.raises(ConfigValidationError, match="headers must be a dictionary"):
            ConfigFileLoader.from_json(config_file)

    def test_invalid_proxies_type(self, tmp_path):
        """Test error with invalid proxies type."""
        config_file = tmp_path / "config.json"
        config_data = {"http_client": {"proxies": "invalid"}}  # Should be dict
        config_file.write_text(json.dumps(config_data))

        with pytest.raises(ConfigValidationError, match="proxies must be a dictionary"):
            ConfigFileLoader.from_json(config_file)

    def test_invalid_root_type(self, tmp_path):
        """Test error when root is not a dictionary."""
        config_file = tmp_path / "config.json"
        config_file.write_text('["not", "a", "dict"]')

        with pytest.raises(ConfigValidationError, match="Config must be a dictionary"):
            ConfigFileLoader.from_json(config_file)


class TestPartialConfig:
    """Test partial configuration (only some fields)."""

    def test_only_base_url(self, tmp_path):
        """Test config with only base_url."""
        config_file = tmp_path / "config.json"
        config_data = {"base_url": "https://api.example.com"}
        config_file.write_text(json.dumps(config_data))

        config = ConfigFileLoader.from_json(config_file)

        assert config.base_url == "https://api.example.com"
        # All other fields should have defaults
        assert config.timeout.connect == 5
        assert config.retry.max_attempts == 3
        assert config.security.verify_ssl is True

    def test_only_timeout(self, tmp_path):
        """Test config with only timeout."""
        config_file = tmp_path / "config.json"
        config_data = {"timeout": {"connect": 30, "read": 90}}
        config_file.write_text(json.dumps(config_data))

        config = ConfigFileLoader.from_json(config_file)

        assert config.timeout.connect == 30
        assert config.timeout.read == 90
        assert config.base_url is None

    def test_pool_config(self, tmp_path):
        """Test pool configuration."""
        pytest.importorskip("yaml")

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
pool:
  connections: 20
  maxsize: 30
  max_redirects: 10
"""
        )

        config = ConfigFileLoader.from_yaml(config_file)

        assert config.pool.pool_connections == 20
        assert config.pool.pool_maxsize == 30
        assert config.pool.max_redirects == 10
