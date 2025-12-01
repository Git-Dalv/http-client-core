"""
Retry engine для умных повторных попыток.

Включает:
- Exponential backoff с jitter
- Retry-After header parsing
- Идемпотентность проверка
"""

import time
import random
from typing import Optional
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from .config import RetryConfig
from .exceptions import FatalError, TemporaryError


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

    def _parse_retry_after(self, response) -> Optional[float]:
        """
        Распарсить Retry-After header.

        Args:
            response: Response объект

        Returns:
            Секунды или None
        """
        if not hasattr(response, 'headers'):
            return None

        retry_after = response.headers.get('Retry-After')
        if not retry_after:
            return None

        try:
            # Попытка как число секунд
            return float(retry_after)
        except ValueError:
            # Попытка как HTTP-date
            try:
                retry_date = parsedate_to_datetime(retry_after)
                delta = (retry_date - datetime.now(timezone.utc)).total_seconds()
                return max(0, delta)
            except Exception:
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
