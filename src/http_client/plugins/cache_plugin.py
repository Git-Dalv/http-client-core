# src/http_client/plugins/cache_plugin.py

import hashlib
import json
import logging
import threading
import time
from typing import Any, Dict, Optional, List, Set

import requests

from .plugin import Plugin

logger = logging.getLogger(__name__)

# Заголовки, которые по умолчанию влияют на кэш ключ
DEFAULT_CACHE_HEADERS = {
    'Accept',
    'Accept-Language',
    'Accept-Encoding',
    'Content-Type',
}


class CachePlugin(Plugin):
    """Плагин для кэширования HTTP ответов"""

    def __init__(
            self,
            ttl: int = 300,
            max_size: int = 1000,
            cache_headers: Optional[Set[str]] = None,
            include_auth_header: bool = False,
    ):
        """
        Args:
            ttl: Time to live для кэша в секундах (по умолчанию 5 минут)
            max_size: Максимальное количество записей в кэше (по умолчанию 1000)
            cache_headers: Набор заголовков для включения в ключ кэша (case-insensitive).
                          По умолчанию: Accept, Accept-Language, Accept-Encoding, Content-Type
            include_auth_header: Включать ли Authorization заголовок в ключ кэша
        """
        self.ttl = ttl
        self.max_size = max_size
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()  # Thread-safe protection for cache operations
        self._hits = 0
        self._misses = 0

        # Используем пользовательский набор заголовков или дефолтный
        self.cache_headers = cache_headers if cache_headers is not None else DEFAULT_CACHE_HEADERS.copy()

        # Добавляем Authorization если требуется
        if include_auth_header:
            self.cache_headers.add('Authorization')

        # Приводим все заголовки к lowercase для case-insensitive сравнения
        self.cache_headers = {h.lower() for h in self.cache_headers}

    def _generate_cache_key(self, method: str, url: str, **kwargs: Any) -> str:
        """
        Генерирует уникальный ключ для кэша на основе:
        - HTTP метода
        - URL
        - Query параметров
        - JSON тела запроса
        - Значимых HTTP заголовков (настраиваемых)
        """
        # Извлекаем значимые заголовки из kwargs
        request_headers = kwargs.get("headers", {})
        significant_headers = {}

        # Включаем только заголовки из списка cache_headers (case-insensitive)
        for header_name, header_value in request_headers.items():
            if header_name.lower() in self.cache_headers:
                significant_headers[header_name.lower()] = header_value

        # Создаем структуру для кэша с методом, URL, параметрами и заголовками
        cache_data = {
            "method": method,
            "url": url,
            "params": kwargs.get("params", {}),
            "json": kwargs.get("json", {}),
            "headers": significant_headers,  # Добавляем значимые заголовки
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

    def _evict_if_needed(self):
        """
        Удаляет старые записи если кэш превысил max_size.
        Использует LRU стратегию (удаляет самые старые по timestamp).

        Должен вызываться внутри lock!
        """
        if len(self.cache) < self.max_size:
            return

        # Удаляем 10% самых старых записей для амортизации
        entries_to_remove = max(1, len(self.cache) // 10)

        # Сортируем по timestamp (самые старые первые)
        sorted_keys = sorted(
            self.cache.keys(),
            key=lambda k: self.cache[k].get("timestamp", 0)
        )

        # Удаляем старые записи
        for key in sorted_keys[:entries_to_remove]:
            del self.cache[key]

        logger.debug(f"Cache eviction: removed {entries_to_remove} entries, size now {len(self.cache)}")

    def get_from_cache(self, method: str, url: str, **kwargs: Any) -> Optional[requests.Response]:
        """Получает ответ из кэша, если он есть и актуален"""
        # Кэшируем только GET запросы
        if method.upper() != "GET":
            return None

        cache_key = self._generate_cache_key(method, url, **kwargs)

        with self._lock:
            cache_entry = self.cache.get(cache_key)

            if self._is_cache_valid(cache_entry):
                self._hits += 1
                logger.debug(f"Cache HIT for {url}")
                return cache_entry["response"]

        self._misses += 1
        logger.debug(f"Cache MISS for {url}")
        return None

    def save_to_cache(self, method: str, url: str, response: requests.Response, **kwargs: Any):
        """Сохраняет ответ в кэш"""
        # Кэшируем только GET запросы с успешным статусом
        if method.upper() != "GET" or response.status_code != 200:
            return

        cache_key = self._generate_cache_key(method, url, **kwargs)
        with self._lock:
            self._evict_if_needed()
            self.cache[cache_key] = {"response": response, "timestamp": time.time()}

    def clear_cache(self):
        """Очищает весь кэш"""
        with self._lock:
            self.cache.clear()
        logger.info("Cache cleared")

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

    @property
    def size(self) -> int:
        """Текущее количество записей в кэше."""
        with self._lock:
            return len(self.cache)

    @property
    def hits(self) -> int:
        """Количество cache hits (для совместимости с примерами)."""
        return self._hits

    @property
    def misses(self) -> int:
        """Количество cache misses (для совместимости с примерами)."""
        return self._misses

    def on_error(self, error: Exception, **kwargs) -> bool:
        """Обработка ошибок"""
        return False  # Не повторять запрос
