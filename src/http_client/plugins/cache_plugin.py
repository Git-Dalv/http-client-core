# src/http_client/plugins/cache_plugin.py

import hashlib
import json
import threading
import time
from typing import Any, Dict, Optional

import requests

from .plugin import Plugin


class CachePlugin(Plugin):
    """Плагин для кэширования HTTP ответов"""

    def __init__(self, ttl: int = 300):
        """
        Args:
            ttl: Time to live для кэша в секундах (по умолчанию 5 минут)
        """
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()  # Thread-safe protection for cache operations

    def _generate_cache_key(self, method: str, url: str, **kwargs: Any) -> str:
        """Генерирует уникальный ключ для кэша"""
        # Создаем строку из метода, URL и параметров
        cache_data = {
            "method": method,
            "url": url,
            "params": kwargs.get("params", {}),
            "json": kwargs.get("json", {}),
        }
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()

    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Проверяет, актуален ли кэш"""
        if not cache_entry:
            return False

        cached_time = cache_entry.get("timestamp", 0)
        current_time = time.time()

        return (current_time - cached_time) < self.ttl

    def get_from_cache(self, method: str, url: str, **kwargs: Any) -> Optional[requests.Response]:
        """Получает ответ из кэша, если он есть и актуален"""
        # Кэшируем только GET запросы
        if method.upper() != "GET":
            return None

        cache_key = self._generate_cache_key(method, url, **kwargs)

        with self._lock:
            cache_entry = self.cache.get(cache_key)

            if self._is_cache_valid(cache_entry):
                print(f"Cache HIT for {url}")
                return cache_entry["response"]

        print(f"Cache MISS for {url}")
        return None

    def save_to_cache(self, method: str, url: str, response: requests.Response, **kwargs: Any):
        """Сохраняет ответ в кэш"""
        # Кэшируем только GET запросы с успешным статусом
        if method.upper() != "GET" or response.status_code != 200:
            return

        cache_key = self._generate_cache_key(method, url, **kwargs)
        with self._lock:
            self.cache[cache_key] = {"response": response, "timestamp": time.time()}

    def clear_cache(self):
        """Очищает весь кэш"""
        with self._lock:
            self.cache.clear()
        print("Cache cleared")

    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        """Проверяет кэш перед запросом"""
        # Сохраняем параметры для использования в after_response
        self._last_request = {"method": method, "url": url, "kwargs": kwargs}
        return kwargs

    def after_response(self, response: requests.Response) -> requests.Response:
        """Сохраняет ответ в кэш"""
        if hasattr(self, "_last_request"):
            self.save_to_cache(
                self._last_request["method"],
                self._last_request["url"],
                response,
                **self._last_request["kwargs"],
            )
        return response

    def on_error(self, error: Exception, **kwargs) -> bool:
        """Обработка ошибок"""
        return False  # Не повторять запрос
