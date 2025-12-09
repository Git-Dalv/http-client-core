"""
Configuration file loader for YAML and JSON files.

Supports loading HTTPClientConfig from external configuration files.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..config import (
    HTTPClientConfig,
    TimeoutConfig,
    RetryConfig,
    ConnectionPoolConfig,
    SecurityConfig,
    CircuitBreakerConfig,
)
from ..logging import LoggingConfig


class ConfigValidationError(Exception):
    """Raised when configuration file is invalid."""

    pass


class ConfigFileLoader:
    """
    Загрузчик конфигурации из файлов.

    Supports YAML and JSON formats with automatic format detection.

    Examples:
        >>> config = ConfigFileLoader.from_yaml("config.yaml")
        >>> config = ConfigFileLoader.from_json("config.json")
        >>> config = ConfigFileLoader.from_file("config.yaml")  # Auto-detect
        >>> config = ConfigFileLoader.from_env_path()  # From HTTP_CLIENT_CONFIG_FILE env var
    """

    @staticmethod
    def from_yaml(path: Union[str, Path]) -> HTTPClientConfig:
        """
        Загрузить конфиг из YAML файла.

        Args:
            path: Путь к YAML файлу

        Returns:
            HTTPClientConfig instance

        Raises:
            FileNotFoundError: Если файл не найден
            ConfigValidationError: Если конфиг невалидный
            ImportError: Если PyYAML не установлен

        Example:
            >>> config = ConfigFileLoader.from_yaml("config.yaml")
            >>> client = HTTPClient(config=config)
        """
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "PyYAML is required to load YAML configs. "
                "Install it with: pip install http-client-core[yaml] or pip install pyyaml"
            )

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Invalid YAML syntax in {path}: {e}")

        if not data:
            raise ConfigValidationError(f"Empty config file: {path}")

        return ConfigFileLoader._build_config(data, str(path))

    @staticmethod
    def from_json(path: Union[str, Path]) -> HTTPClientConfig:
        """
        Загрузить конфиг из JSON файла.

        Args:
            path: Путь к JSON файлу

        Returns:
            HTTPClientConfig instance

        Raises:
            FileNotFoundError: Если файл не найден
            ConfigValidationError: Если конфиг невалидный

        Example:
            >>> config = ConfigFileLoader.from_json("config.json")
            >>> client = HTTPClient(config=config)
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigValidationError(f"Invalid JSON syntax in {path}: {e}")

        if not data:
            raise ConfigValidationError(f"Empty config file: {path}")

        return ConfigFileLoader._build_config(data, str(path))

    @staticmethod
    def from_file(path: Union[str, Path]) -> HTTPClientConfig:
        """
        Автоопределение формата по расширению (.yaml, .yml, .json).

        Args:
            path: Путь к конфиг файлу

        Returns:
            HTTPClientConfig instance

        Raises:
            ValueError: Если формат не поддерживается
            FileNotFoundError: Если файл не найден
            ConfigValidationError: Если конфиг невалидный

        Example:
            >>> config = ConfigFileLoader.from_file("config.yaml")
        """
        path = Path(path)
        suffix = path.suffix.lower()

        if suffix in [".yaml", ".yml"]:
            return ConfigFileLoader.from_yaml(path)
        elif suffix == ".json":
            return ConfigFileLoader.from_json(path)
        else:
            raise ValueError(
                f"Unsupported config file format: {suffix}. "
                f"Supported formats: .yaml, .yml, .json"
            )

    @staticmethod
    def from_env_path() -> Optional[HTTPClientConfig]:
        """
        Загрузить из пути указанного в HTTP_CLIENT_CONFIG_FILE env var.

        Returns:
            HTTPClientConfig instance or None if env var not set

        Raises:
            FileNotFoundError: Если файл не найден
            ConfigValidationError: Если конфиг невалидный

        Example:
            >>> # export HTTP_CLIENT_CONFIG_FILE=/path/to/config.yaml
            >>> config = ConfigFileLoader.from_env_path()
            >>> if config:
            ...     client = HTTPClient(config=config)
        """
        config_path = os.environ.get("HTTP_CLIENT_CONFIG_FILE")
        if not config_path:
            return None

        return ConfigFileLoader.from_file(config_path)

    @staticmethod
    def _build_config(data: Dict[str, Any], source: str) -> HTTPClientConfig:
        """
        Build HTTPClientConfig from parsed data.

        Args:
            data: Parsed config data
            source: Source file path (for error messages)

        Returns:
            HTTPClientConfig instance

        Raises:
            ConfigValidationError: If config is invalid
        """
        # Extract http_client section if present
        if "http_client" in data:
            config_data = data["http_client"]
        else:
            config_data = data

        if not isinstance(config_data, dict):
            raise ConfigValidationError(
                f"Config must be a dictionary, got {type(config_data).__name__} in {source}"
            )

        try:
            # Build timeout config
            timeout_cfg = TimeoutConfig()
            if "timeout" in config_data:
                timeout_data = config_data["timeout"]
                if not isinstance(timeout_data, dict):
                    raise ConfigValidationError(
                        f"timeout must be a dictionary in {source}"
                    )
                timeout_cfg = TimeoutConfig(
                    connect=timeout_data.get("connect", 5),
                    read=timeout_data.get("read", 30),
                    total=timeout_data.get("total"),
                )

            # Build retry config
            retry_cfg = RetryConfig()
            if "retry" in config_data:
                retry_data = config_data["retry"]
                if not isinstance(retry_data, dict):
                    raise ConfigValidationError(
                        f"retry must be a dictionary in {source}"
                    )

                # Build kwargs for RetryConfig
                retry_kwargs = {}
                if "max_attempts" in retry_data:
                    retry_kwargs["max_attempts"] = retry_data["max_attempts"]
                if "backoff_base" in retry_data:
                    retry_kwargs["backoff_base"] = retry_data["backoff_base"]
                if "backoff_factor" in retry_data:
                    retry_kwargs["backoff_factor"] = retry_data["backoff_factor"]
                if "backoff_max" in retry_data:
                    retry_kwargs["backoff_max"] = retry_data["backoff_max"]
                if "backoff_jitter" in retry_data:
                    retry_kwargs["backoff_jitter"] = retry_data["backoff_jitter"]

                # Handle retry_on_status (convert to retryable_status_codes)
                if "retry_on_status" in retry_data:
                    retry_kwargs["retryable_status_codes"] = set(
                        retry_data["retry_on_status"]
                    )

                retry_cfg = RetryConfig(**retry_kwargs)

            # Build pool config
            pool_cfg = ConnectionPoolConfig()
            if "pool" in config_data:
                pool_data = config_data["pool"]
                if not isinstance(pool_data, dict):
                    raise ConfigValidationError(
                        f"pool must be a dictionary in {source}"
                    )
                pool_cfg = ConnectionPoolConfig(
                    pool_connections=pool_data.get("connections", 10),
                    pool_maxsize=pool_data.get("maxsize", 10),
                    pool_block=pool_data.get("block", False),
                    max_redirects=pool_data.get("max_redirects", 30),
                )

            # Build security config
            security_cfg = SecurityConfig()
            if "security" in config_data:
                security_data = config_data["security"]
                if not isinstance(security_data, dict):
                    raise ConfigValidationError(
                        f"security must be a dictionary in {source}"
                    )
                security_cfg = SecurityConfig(
                    max_response_size=security_data.get(
                        "max_response_size", 100 * 1024 * 1024
                    ),
                    max_decompressed_size=security_data.get(
                        "max_decompressed_size", 500 * 1024 * 1024
                    ),
                    max_compression_ratio=security_data.get(
                        "max_compression_ratio", 20.0
                    ),
                    verify_ssl=security_data.get("verify_ssl", True),
                    allow_redirects=security_data.get("allow_redirects", True),
                )

            # Build circuit breaker config
            circuit_breaker_cfg = CircuitBreakerConfig()
            if "circuit_breaker" in config_data:
                cb_data = config_data["circuit_breaker"]
                if not isinstance(cb_data, dict):
                    raise ConfigValidationError(
                        f"circuit_breaker must be a dictionary in {source}"
                    )
                circuit_breaker_cfg = CircuitBreakerConfig(
                    enabled=cb_data.get("enabled", False),
                    failure_threshold=cb_data.get("failure_threshold", 5),
                    recovery_timeout=cb_data.get("recovery_timeout", 30.0),
                    half_open_max_calls=cb_data.get("half_open_max_calls", 3),
                )

            # Build logging config
            logging_cfg = None
            if "logging" in config_data:
                logging_data = config_data["logging"]
                if not isinstance(logging_data, dict):
                    raise ConfigValidationError(
                        f"logging must be a dictionary in {source}"
                    )
                logging_cfg = LoggingConfig.create(
                    level=logging_data.get("level", "INFO"),
                    format=logging_data.get("format", "text"),
                    enable_console=logging_data.get("enable_console", True),
                    enable_file=logging_data.get("enable_file", False),
                    file_path=logging_data.get("file_path"),
                    enable_correlation_id=logging_data.get(
                        "enable_correlation_id", False
                    ),
                )

            # Extract headers and proxies
            headers = config_data.get("headers", {})
            if not isinstance(headers, dict):
                raise ConfigValidationError(
                    f"headers must be a dictionary in {source}"
                )

            proxies = config_data.get("proxies", {})
            if not isinstance(proxies, dict):
                raise ConfigValidationError(
                    f"proxies must be a dictionary in {source}"
                )

            # Build final config
            return HTTPClientConfig(
                base_url=config_data.get("base_url"),
                headers=headers,
                proxies=proxies,
                timeout=timeout_cfg,
                retry=retry_cfg,
                pool=pool_cfg,
                security=security_cfg,
                circuit_breaker=circuit_breaker_cfg,
                logging=logging_cfg,
            )

        except (ValueError, TypeError) as e:
            raise ConfigValidationError(f"Invalid config in {source}: {e}")
