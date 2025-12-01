"""Тесты RetryEngine."""

import pytest
import time
from unittest.mock import Mock
from src.http_client.core.retry_engine import RetryEngine
from src.http_client.core.config import RetryConfig
from src.http_client.core.exceptions import (
    TimeoutError,
    ServerError,
    BadRequestError,
    TooManyRequestsError,
)


def test_retry_engine_init():
    """Тест инициализации."""
    config = RetryConfig()
    engine = RetryEngine(config)
    assert engine.attempt == 0


def test_should_retry_timeout_error():
    """Retry для TimeoutError."""
    config = RetryConfig(max_attempts=3)
    engine = RetryEngine(config)

    error = TimeoutError("Timeout", "https://example.com")
    assert engine.should_retry('GET', error) is True


def test_should_retry_server_error():
    """Retry для ServerError."""
    config = RetryConfig()
    engine = RetryEngine(config)

    error = ServerError(500, "https://example.com")
    assert engine.should_retry('GET', error) is True


def test_should_not_retry_fatal():
    """НЕ retry для fatal ошибок."""
    config = RetryConfig()
    engine = RetryEngine(config)

    error = BadRequestError("https://example.com")
    assert engine.should_retry('GET', error) is False


def test_should_not_retry_non_idempotent():
    """НЕ retry для POST."""
    config = RetryConfig()
    engine = RetryEngine(config)

    error = TimeoutError("Timeout", "https://example.com")
    assert engine.should_retry('POST', error) is False


def test_should_not_retry_max_attempts():
    """НЕ retry после лимита."""
    config = RetryConfig(max_attempts=2)
    engine = RetryEngine(config)

    error = TimeoutError("Timeout", "https://example.com")

    engine.increment()
    engine.increment()

    assert engine.should_retry('GET', error) is False


def test_get_wait_time_exponential():
    """Exponential backoff."""
    config = RetryConfig(
        backoff_base=1.0,
        backoff_factor=2.0,
        backoff_jitter=False
    )
    engine = RetryEngine(config)

    # Попытка 0: 1.0 * 2^0 = 1.0
    wait = engine.get_wait_time()
    assert wait == 1.0

    # Попытка 1: 1.0 * 2^1 = 2.0
    engine.increment()
    wait = engine.get_wait_time()
    assert wait == 2.0

    # Попытка 2: 1.0 * 2^2 = 4.0
    engine.increment()
    wait = engine.get_wait_time()
    assert wait == 4.0


def test_get_wait_time_max():
    """Ограничение максимума."""
    config = RetryConfig(
        backoff_base=10.0,
        backoff_factor=10.0,
        backoff_max=30.0,
        backoff_jitter=False
    )
    engine = RetryEngine(config)

    engine._attempt = 5  # Большая попытка
    wait = engine.get_wait_time()

    assert wait == 30.0  # Не больше max


def test_get_wait_time_jitter():
    """Jitter работает."""
    config = RetryConfig(
        backoff_base=10.0,
        backoff_factor=1.0,
        backoff_jitter=True
    )
    engine = RetryEngine(config)

    # Jitter: 50-150% от 10.0 = 5.0 to 15.0
    wait = engine.get_wait_time()
    assert 5.0 <= wait <= 15.0


def test_parse_retry_after_seconds():
    """Retry-After как секунды."""
    config = RetryConfig()
    engine = RetryEngine(config)

    response = Mock()
    response.headers = {'Retry-After': '60'}

    wait = engine._parse_retry_after(response)
    assert wait == 60.0


def test_reset():
    """Сброс счётчика."""
    config = RetryConfig()
    engine = RetryEngine(config)

    engine.increment()
    engine.increment()
    assert engine.attempt == 2

    engine.reset()
    assert engine.attempt == 0


def test_should_retry_by_status_code():
    """Retry по статус коду в response."""
    config = RetryConfig()
    engine = RetryEngine(config)

    # Обычный exception без retryable/fatal атрибутов
    error = Exception("Generic error")

    # Mock response со статусом 503
    response = Mock()
    response.status_code = 503

    assert engine.should_retry('GET', error, response) is True


def test_should_not_retry_non_retryable_status():
    """НЕ retry для не-retryable статусов."""
    config = RetryConfig()
    engine = RetryEngine(config)

    error = Exception("Generic error")

    response = Mock()
    response.status_code = 200  # OK - не ретраим

    assert engine.should_retry('GET', error, response) is False


def test_get_wait_time_with_retry_after():
    """Приоритет Retry-After header."""
    config = RetryConfig(
        backoff_base=10.0,
        respect_retry_after=True
    )
    engine = RetryEngine(config)

    response = Mock()
    response.headers = {'Retry-After': '120'}

    # Должен использовать 120 из header, а не backoff
    wait = engine.get_wait_time(response=response)
    assert wait == 120.0


def test_get_wait_time_retry_after_max_limit():
    """Retry-After ограничен максимумом."""
    config = RetryConfig(
        retry_after_max=100,
        respect_retry_after=True
    )
    engine = RetryEngine(config)

    response = Mock()
    response.headers = {'Retry-After': '500'}

    # Должен ограничить 500 до 100
    wait = engine.get_wait_time(response=response)
    assert wait == 100.0


def test_parse_retry_after_no_header():
    """Нет Retry-After header."""
    config = RetryConfig()
    engine = RetryEngine(config)

    response = Mock()
    response.headers = {}

    wait = engine._parse_retry_after(response)
    assert wait is None


def test_parse_retry_after_no_headers_attr():
    """Response без атрибута headers."""
    config = RetryConfig()
    engine = RetryEngine(config)

    response = Mock(spec=[])  # Нет headers

    wait = engine._parse_retry_after(response)
    assert wait is None


def test_parse_retry_after_http_date():
    """Retry-After как HTTP date."""
    from datetime import datetime, timedelta, timezone

    config = RetryConfig()
    engine = RetryEngine(config)

    # Создать дату через 60 секунд от сейчас
    future_time = datetime.now(timezone.utc) + timedelta(seconds=60)
    http_date = future_time.strftime('%a, %d %b %Y %H:%M:%S GMT')

    response = Mock()
    response.headers = {'Retry-After': http_date}

    wait = engine._parse_retry_after(response)
    # Должно быть около 60 секунд (±5 для погрешности)
    assert wait is not None
    assert 55 <= wait <= 65


def test_parse_retry_after_invalid_format():
    """Невалидный формат Retry-After."""
    config = RetryConfig()
    engine = RetryEngine(config)

    response = Mock()
    response.headers = {'Retry-After': 'invalid-format'}

    wait = engine._parse_retry_after(response)
    assert wait is None
