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

def test_http_client_config_headers_immutable():
    """Тест что headers нельзя мутировать после создания."""
    config = HTTPClientConfig(headers={"X-Test": "value"})

    # Проверяем что это Mapping
    from typing import Mapping
    assert isinstance(config.headers, Mapping)

    # Попытка изменить должна вызвать TypeError
    with pytest.raises(TypeError):
        config.headers["X-New"] = "fail"

def test_http_client_config_proxies_immutable():
    """Тест что proxies нельзя мутировать после создания."""
    config = HTTPClientConfig(proxies={"http": "http://proxy:8080"})

    # Проверяем что это Mapping
    from typing import Mapping
    assert isinstance(config.proxies, Mapping)

    # Попытка изменить должна вызвать TypeError
    with pytest.raises(TypeError):
        config.proxies["https"] = "https://proxy:8080"

def test_http_client_config_create_accepts_dict():
    """Тест что create() принимает обычный dict."""
    headers_dict = {"Authorization": "Bearer token"}
    proxies_dict = {"http": "http://proxy:8080"}

    config = HTTPClientConfig.create(
        headers=headers_dict,
        proxies=proxies_dict
    )

    # Проверяем что headers и proxies заморожены
    with pytest.raises(TypeError):
        config.headers["X-New"] = "fail"

    with pytest.raises(TypeError):
        config.proxies["https"] = "https://proxy:8080"

    # Проверяем что оригинальные dict не были изменены
    assert headers_dict == {"Authorization": "Bearer token"}
    assert proxies_dict == {"http": "http://proxy:8080"}

def test_http_client_config_with_headers():
    """Тест метода with_headers() возвращает новый immutable config."""
    config = HTTPClientConfig(headers={"X-Original": "value"})
    new_config = config.with_headers({"X-New": "new_value"})

    # Проверяем что оригинальный конфиг не изменился
    assert "X-New" not in config.headers
    assert config.headers["X-Original"] == "value"

    # Проверяем что новый конфиг содержит оба заголовка
    assert new_config.headers["X-Original"] == "value"
    assert new_config.headers["X-New"] == "new_value"

    # Проверяем что новый конфиг тоже immutable
    with pytest.raises(TypeError):
        new_config.headers["X-Another"] = "fail"

def test_http_client_config_headers_dict_not_mutated():
    """Тест что оригинальный dict не мутируется."""
    headers_dict = {"X-Test": "value"}
    config = HTTPClientConfig(headers=headers_dict)

    # Изменяем оригинальный dict
    headers_dict["X-New"] = "new_value"

    # Проверяем что config.headers не изменился
    assert "X-New" not in config.headers
    assert dict(config.headers) == {"X-Test": "value"}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SecurityConfig
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_security_config_insecure_warning_raised():
    """Тест что InsecureRequestWarning выдается при verify_ssl=False."""
    import warnings
    from src.http_client.core.exceptions import InsecureRequestWarning

    with warnings.catch_warnings(record=True) as w:
        # Enable all warnings
        warnings.simplefilter("always")

        # Create config with SSL verification disabled
        config = SecurityConfig(verify_ssl=False)

        # Check that warning was raised
        assert len(w) == 1
        assert issubclass(w[0].category, InsecureRequestWarning)
        assert "SSL verification is disabled" in str(w[0].message)
        assert "man-in-the-middle" in str(w[0].message)

def test_security_config_no_warning_when_ssl_enabled():
    """Тест что warning НЕ выдается при verify_ssl=True (по умолчанию)."""
    import warnings

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        # Create config with SSL verification enabled (default)
        config = SecurityConfig(verify_ssl=True)

        # Check that no warnings were raised
        assert len(w) == 0

def test_security_config_insecure_warning_in_http_client_config():
    """Тест что InsecureRequestWarning выдается через HTTPClientConfig.create()."""
    import warnings
    from src.http_client.core.exceptions import InsecureRequestWarning

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        # Create config with SSL verification disabled
        config = HTTPClientConfig.create(verify_ssl=False)

        # Check that warning was raised
        assert len(w) == 1
        assert issubclass(w[0].category, InsecureRequestWarning)
        assert "SSL verification is disabled" in str(w[0].message)
