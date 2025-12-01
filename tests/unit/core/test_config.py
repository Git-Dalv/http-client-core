"""Тесты для системы конфигурации."""

import pytest
from src.http_client.core.config import (
    TimeoutConfig,
    RetryConfig,
    ConnectionPoolConfig,
    SecurityConfig,
    HTTPClientConfig,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TimeoutConfig
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_timeout_config_defaults():
    """Тест дефолтных значений."""
    config = TimeoutConfig()
    assert config.connect == 5
    assert config.read == 30
    assert config.total is None

def test_timeout_config_custom():
    """Тест кастомных значений."""
    config = TimeoutConfig(connect=10, read=60, total=120)
    assert config.connect == 10
    assert config.read == 60
    assert config.total == 120

def test_timeout_config_as_tuple():
    """Тест метода as_tuple."""
    config = TimeoutConfig(connect=3, read=45)
    assert config.as_tuple() == (3, 45)

def test_timeout_config_validation_negative_connect():
    """Тест валидации - отрицательный connect."""
    with pytest.raises(ValueError, match="connect timeout must be positive"):
        TimeoutConfig(connect=-1)

def test_timeout_config_validation_negative_read():
    """Тест валидации - отрицательный read."""
    with pytest.raises(ValueError, match="read timeout must be positive"):
        TimeoutConfig(read=-1)

def test_timeout_config_immutable():
    """Тест immutability."""
    config = TimeoutConfig()
    with pytest.raises(Exception):  # frozen dataclass
        config.connect = 10

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RetryConfig
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_retry_config_defaults():
    """Тест дефолтных значений."""
    config = RetryConfig()
    assert config.max_attempts == 3
    assert config.backoff_base == 0.5
    assert config.backoff_factor == 2.0
    assert config.backoff_max == 60.0
    assert config.backoff_jitter is True
    assert 'GET' in config.idempotent_methods
    assert 500 in config.retryable_status_codes

def test_retry_config_custom():
    """Тест кастомных значений."""
    config = RetryConfig(
        max_attempts=5,
        backoff_base=1.0,
        backoff_max=120.0
    )
    assert config.max_attempts == 5
    assert config.backoff_base == 1.0
    assert config.backoff_max == 120.0

def test_retry_config_validation():
    """Тест валидации."""
    with pytest.raises(ValueError):
        RetryConfig(max_attempts=-1)

    with pytest.raises(ValueError):
        RetryConfig(backoff_factor=0.5)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HTTPClientConfig
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_http_client_config_defaults():
    """Тест дефолтных значений."""
    config = HTTPClientConfig()
    assert config.base_url is None
    assert config.headers == {}
    assert isinstance(config.timeout, TimeoutConfig)
    assert isinstance(config.retry, RetryConfig)

def test_http_client_config_create_simple():
    """Тест create() с простыми параметрами."""
    config = HTTPClientConfig.create(
        base_url="https://api.example.com",
        timeout=60
    )
    assert config.base_url == "https://api.example.com"
    assert config.timeout.read == 60

def test_http_client_config_create_tuple_timeout():
    """Тест create() с tuple timeout."""
    config = HTTPClientConfig.create(timeout=(10, 90))
    assert config.timeout.connect == 10
    assert config.timeout.read == 90

def test_http_client_config_create_separate_timeouts():
    """Тест create() с отдельными connect/read."""
    config = HTTPClientConfig.create(
        connect_timeout=3,
        read_timeout=120
    )
    assert config.timeout.connect == 3
    assert config.timeout.read == 120

def test_http_client_config_with_timeout():
    """Тест метода with_timeout()."""
    config = HTTPClientConfig()
    new_config = config.with_timeout(90)

    assert config.timeout.read == 30  # Оригинал не изменился
    assert new_config.timeout.read == 90

def test_http_client_config_with_retries():
    """Тест метода with_retries()."""
    config = HTTPClientConfig()
    new_config = config.with_retries(10)

    assert config.retry.max_attempts == 3
    assert new_config.retry.max_attempts == 10

def test_http_client_config_immutable():
    """Тест immutability."""
    config = HTTPClientConfig()
    with pytest.raises(Exception):
        config.base_url = "https://new.com"
