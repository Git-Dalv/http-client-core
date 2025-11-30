# src/http_client/plugins/rate_limit_plugin.py

import time
from collections import deque
from typing import Any, Dict

import requests

from .plugin import Plugin


class RateLimitPlugin(Plugin):
    """Плагин для ограничения частоты запросов"""

    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        Инициализация плагина rate limiting.

        Args:
            max_requests: Максимальное количество запросов
            time_window: Временное окно в секундах
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_times = deque()

    def _clean_old_requests(self):
        """Удаляет старые запросы из очереди"""
        current_time = time.time()
        while self.request_times and (current_time - self.request_times[0]) > self.time_window:
            self.request_times.popleft()

    def _should_throttle(self) -> bool:
        """Проверяет, нужно ли ограничить запрос"""
        self._clean_old_requests()
        return len(self.request_times) >= self.max_requests

    def _wait_if_needed(self):
        """Ожидает, если достигнут лимит запросов"""
        if self._should_throttle():
            oldest_request = self.request_times[0]
            wait_time = self.time_window - (time.time() - oldest_request)

            if wait_time > 0:
                print(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                self._clean_old_requests()

    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        """Проверяет rate limit перед запросом"""
        self._wait_if_needed()
        self.request_times.append(time.time())
        return kwargs

    def after_response(self, response: requests.Response) -> requests.Response:
        """Обработка после получения ответа"""
        return response

    def on_error(self, error: Exception) -> None:
        """Обработка ошибок"""
        if self.request_times:
            self.request_times.pop()

    def reset(self):
        """Сбрасывает счетчик запросов"""
        self.request_times.clear()
        print("Rate limit counter reset")

    def get_remaining_requests(self) -> int:
        """Возвращает количество оставшихся запросов"""
        self._clean_old_requests()
        return max(0, self.max_requests - len(self.request_times))

    def get_reset_time(self) -> float:
        """Возвращает время до сброса лимита в секундах"""
        if not self.request_times:
            return 0.0

        self._clean_old_requests()

        if len(self.request_times) < self.max_requests:
            return 0.0

        oldest_request = self.request_times[0]
        reset_time = self.time_window - (time.time() - oldest_request)
        return max(0.0, reset_time)
