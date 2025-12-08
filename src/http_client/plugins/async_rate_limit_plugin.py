# src/http_client/plugins/async_rate_limit_plugin.py
"""
Async плагин для ограничения частоты запросов (rate limiting).

Использует asyncio.Lock и asyncio.sleep для неблокирующих операций.
"""

import asyncio
import logging
import time
from collections import deque
from typing import Any, Dict

from .async_plugin import AsyncPlugin
from .plugin import PluginPriority

logger = logging.getLogger(__name__)


class AsyncRateLimitPlugin(AsyncPlugin):
    """
    Async плагин для ограничения частоты запросов.

    Priority: HIGH (25) - должен выполняться рано, чтобы защитить API от перегрузки.

    Использует sliding window алгоритм для точного контроля rate limit.
    Не блокирует event loop при ожидании.

    Example:
        >>> # Максимум 10 запросов за 60 секунд
        >>> rate_limiter = AsyncRateLimitPlugin(max_requests=10, time_window=60)
        >>> client = AsyncHTTPClient(plugins=[rate_limiter])
        >>>
        >>> # Запросы будут автоматически throttled
        >>> for i in range(15):
        ...     response = await client.get("https://api.example.com/data")
    """

    priority = PluginPriority.HIGH

    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        Args:
            max_requests: Максимальное количество запросов
            time_window: Временное окно в секундах
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_times = deque()
        self._lock = asyncio.Lock()  # Async lock для thread-safety

    def _clean_old_requests(self):
        """Удаляет старые запросы из очереди."""
        current_time = time.time()
        while self.request_times and (current_time - self.request_times[0]) > self.time_window:
            self.request_times.popleft()

    def _should_throttle(self) -> bool:
        """Проверяет, нужно ли ограничить запрос."""
        self._clean_old_requests()
        return len(self.request_times) >= self.max_requests

    async def _wait_if_needed(self):
        """Ожидает, если достигнут лимит запросов (async)."""
        if self._should_throttle():
            oldest_request = self.request_times[0]
            wait_time = self.time_window - (time.time() - oldest_request)

            if wait_time > 0:
                logger.warning(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
                await asyncio.sleep(wait_time)
                self._clean_old_requests()

    async def before_request(
        self,
        method: str,
        url: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Проверяет rate limit перед запросом.

        Если достигнут лимит - асинхронно ждет.
        """
        async with self._lock:
            await self._wait_if_needed()
            self.request_times.append(time.time())
        return kwargs

    async def after_response(self, response):
        """Обработка после получения ответа."""
        return response

    async def on_error(self, error: Exception, **kwargs: Any) -> None:
        """
        Обработка ошибок.

        При ошибке удаляем последний запрос из счетчика.
        """
        async with self._lock:
            if self.request_times:
                self.request_times.pop()

    async def reset(self):
        """Сбрасывает счетчик запросов."""
        async with self._lock:
            self.request_times.clear()
        logger.info("Rate limit counter reset")

    async def get_remaining_requests(self) -> int:
        """Возвращает количество оставшихся запросов."""
        async with self._lock:
            self._clean_old_requests()
            return max(0, self.max_requests - len(self.request_times))

    async def get_reset_time(self) -> float:
        """Возвращает время до сброса лимита в секундах."""
        async with self._lock:
            if not self.request_times:
                return 0.0

            self._clean_old_requests()

            if len(self.request_times) < self.max_requests:
                return 0.0

            oldest_request = self.request_times[0]
            reset_time = self.time_window - (time.time() - oldest_request)
            return max(0.0, reset_time)

    async def get_stats(self) -> Dict[str, Any]:
        """
        Получить статистику rate limiter.

        Returns:
            Dict с current_requests, max_requests, remaining, reset_time
        """
        async with self._lock:
            self._clean_old_requests()
            return {
                "current_requests": len(self.request_times),
                "max_requests": self.max_requests,
                "remaining": max(0, self.max_requests - len(self.request_times)),
                "time_window": self.time_window,
                "reset_time": await self.get_reset_time(),
            }
