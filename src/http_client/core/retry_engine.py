"""
Retry engine для умных повторных попыток.

Включает:
- Exponential backoff с jitter
- Retry-After header parsing
- Идемпотентность проверка
"""

import logging
import time
import random
import asyncio
from typing import Optional
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from .config import RetryConfig
from .exceptions import FatalError, TemporaryError

logger = logging.getLogger(__name__)


class RetryEngine:
    """
    Механизм retry с умной логикой.

    Examples:
        >>> config = RetryConfig(max_attempts=3)
        >>> engine = RetryEngine(config)
        >>> if engine.should_retry('GET', error, response):
        >>>     wait = engine.get_wait_time(error, response)
        >>>     time.sleep(wait)
        >>>     engine.increment()
    """

    def __init__(self, config: RetryConfig):
        """
        Args:
            config: Конфигурация retry
        """
        self.config = config
        self._attempt = 0

    def should_retry(
        self,
        method: str,
        error: Exception,
        response = None
    ) -> bool:
        """
        Решить нужен ли retry.

        Args:
            method: HTTP метод (GET, POST, etc)
            error: Исключение
            response: Response объект (если есть)

        Returns:
            True если нужен retry
        """
        # Проверка лимита попыток (проверяем, не превысит ли следующая попытка лимит)
        if self._attempt + 1 >= self.config.max_attempts:
            return False

        # Проверка идемпотентности
        if method.upper() not in self.config.idempotent_methods:
            return False

        # Фатальные ошибки НЕ ретраим
        if hasattr(error, 'fatal') and error.fatal:
            return False

        # Временные ошибки ретраим
        if hasattr(error, 'retryable') and error.retryable:
            return True

        # Проверка статус кода
        if response and hasattr(response, 'status_code'):
            if response.status_code in self.config.retryable_status_codes:
                return True

        return False

    def get_wait_time(
        self,
        error: Exception = None,
        response = None
    ) -> float:
        """
        Вычислить время ожидания.

        Args:
            error: Исключение (опционально)
            response: Response (опционально)

        Returns:
            Секунды для ожидания
        """
        # Приоритет 1: Retry-After header
        if self.config.respect_retry_after and response:
            retry_after = self._parse_retry_after(response)
            if retry_after is not None:
                return min(retry_after, self.config.retry_after_max)

        # Приоритет 2: Exponential backoff
        wait = self.config.backoff_base * (
            self.config.backoff_factor ** self._attempt
        )

        # Ограничить максимумом
        wait = min(wait, self.config.backoff_max)

        # Добавить jitter (50-150% от wait)
        if self.config.backoff_jitter:
            jitter = 0.5 + random.random()  # 0.5 to 1.5
            wait = wait * jitter

        return wait

    async def async_wait(
        self,
        error: Exception = None,
        response = None
    ) -> None:
        """
        Асинхронное ожидание перед retry (async-версия).

        Args:
            error: Исключение (опционально)
            response: Response (опционально)

        Examples:
            >>> await engine.async_wait(error, response)
        """
        wait_time = self.get_wait_time(error, response)
        await asyncio.sleep(wait_time)

    def _parse_retry_after(self, response) -> Optional[float]:
        """
        Распарсить Retry-After header с валидацией против malicious input.

        Args:
            response: Response объект

        Returns:
            Секунды или None

        Security:
            - Ограничивает длину header для защиты от DoS
            - Безопасно обрабатывает malformed input
            - Логирует подозрительные значения
        """
        if not hasattr(response, 'headers'):
            return None

        retry_after = response.headers.get('Retry-After')
        if not retry_after:
            return None

        # Защита от oversized header (DoS attack)
        # Нормальные значения: "60" или "Wed, 21 Oct 2015 07:28:00 GMT"
        MAX_HEADER_LENGTH = 100
        if len(retry_after) > MAX_HEADER_LENGTH:
            logger.warning(
                f"Retry-After header too long ({len(retry_after)} chars), ignoring. "
                f"Value: {retry_after[:50]}..."
            )
            return None

        try:
            # Попытка как число секунд
            seconds = float(retry_after)
            # Валидация разумного диапазона
            if seconds < 0 or seconds > 86400 * 365:  # Не больше года
                logger.warning(
                    f"Retry-After seconds value out of reasonable range: {seconds}"
                )
                return None
            return seconds
        except ValueError:
            # Попытка как HTTP-date
            try:
                retry_date = parsedate_to_datetime(retry_after)
                delta = (retry_date - datetime.now(timezone.utc)).total_seconds()
                return max(0, delta)
            except (ValueError, TypeError, OverflowError) as e:
                # Более строгая обработка ошибок parsedate_to_datetime
                logger.debug(
                    f"Failed to parse Retry-After header '{retry_after}': {e}"
                )
                return None
            except Exception as e:
                # Catch-all для неожиданных ошибок
                logger.warning(
                    f"Unexpected error parsing Retry-After header '{retry_after}': {e}"
                )
                return None

    def increment(self):
        """Увеличить счётчик попыток."""
        self._attempt += 1

    def reset(self):
        """Сбросить счётчик."""
        self._attempt = 0

    @property
    def attempt(self) -> int:
        """Текущая попытка."""
        return self._attempt
