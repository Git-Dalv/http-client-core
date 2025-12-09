# src/http_client/plugins/async_cache_plugin.py
"""
Async плагин для кэширования HTTP ответов.

Использует asyncio.Lock вместо threading.RLock для безопасной работы в async контексте.
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from typing import Any, Dict, Optional, Set

try:
    import httpx
except ImportError:
    httpx = None

from .async_plugin import AsyncPlugin
from .plugin import PluginPriority

logger = logging.getLogger(__name__)

# Заголовки, которые по умолчанию влияют на кэш ключ
DEFAULT_CACHE_HEADERS = {
    'Accept',
    'Accept-Language',
    'Accept-Encoding',
    'Content-Type',
}


class AsyncCachePlugin(AsyncPlugin):
    """
    Async плагин для кэширования HTTP ответов.

    Priority: CACHE (10) - должен быть рано, но после Auth плагинов.

    Использует async lock для thread-safety в async контексте.
    Кэширует только GET запросы с успешными ответами (200-299).

    Example:
        >>> cache = AsyncCachePlugin(ttl=300, max_size=1000)
        >>> client = AsyncHTTPClient(plugins=[cache])
        >>> # Первый запрос - miss
        >>> response = await client.get("https://api.example.com/data")
        >>> # Второй запрос - hit (из кэша)
        >>> response = await client.get("https://api.example.com/data")
    """

    priority = PluginPriority.CACHE

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
            max_size: Максимальное количество записей в кэше
            cache_headers: Набор заголовков для включения в ключ кэша
            include_auth_header: Включать ли Authorization в ключ кэша
        """
        self.ttl = ttl
        self.max_size = max_size
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()  # LRU ordering
        self._lock = asyncio.Lock()  # Async lock для thread-safety
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
        Генерирует уникальный ключ для кэша.

        Учитывает:
        - HTTP метод
        - URL
        - Query параметры
        - JSON тело запроса
        - Значимые HTTP заголовки
        """
        # Извлекаем значимые заголовки
        request_headers = kwargs.get("headers", {})
        significant_headers = {}

        for header_name, header_value in request_headers.items():
            if header_name.lower() in self.cache_headers:
                significant_headers[header_name.lower()] = header_value

        # Создаем структуру для кэша
        cache_data = {
            "method": method,
            "url": url,
            "params": kwargs.get("params"),
            "json": kwargs.get("json"),
            "data": kwargs.get("data"),
            "headers": significant_headers,
        }

        # Сериализуем и хэшируем
        cache_str = json.dumps(cache_data, sort_keys=True)
        # Use SHA256 (truncate to 32 chars for consistency with cache_plugin.py)
        return hashlib.sha256(cache_str.encode()).hexdigest()[:32]

    async def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Получить значение из кэша (async)."""
        async with self._lock:
            if cache_key not in self.cache:
                self._misses += 1
                return None

            entry = self.cache[cache_key]

            # Проверяем TTL через expires_at
            if time.time() >= entry["expires_at"]:
                # Устарело - удаляем
                del self.cache[cache_key]
                self._misses += 1
                return None

            # Move to end for LRU ordering (mark as recently used)
            self.cache.move_to_end(cache_key, last=True)

            self._hits += 1
            return entry["response"]

    async def _put_to_cache(self, cache_key: str, response: Any) -> None:
        """Сохранить в кэш (async)."""
        async with self._lock:
            # Проверяем размер кэша
            if len(self.cache) >= self.max_size:
                # Удаляем самую старую запись (LRU) через OrderedDict.popitem(last=False)
                # О(1) операция вместо O(n) через min()
                self.cache.popitem(last=False)

            # Сохраняем с expires_at для TTL validation
            self.cache[cache_key] = {
                "response": response,
                "expires_at": time.time() + self.ttl,
            }

    async def before_request(
        self,
        method: str,
        url: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Проверяем кэш перед запросом.

        Если есть закэшированный ответ - возвращаем его через специальный ключ.
        """
        # Кэшируем только GET запросы
        if method.upper() != "GET":
            return kwargs

        cache_key = self._generate_cache_key(method, url, **kwargs)
        cached_response = await self._get_from_cache(cache_key)

        if cached_response is not None:
            # Возвращаем закэшированный ответ через специальный ключ
            kwargs["__cached_response__"] = cached_response
            logger.debug(f"Cache HIT for {method} {url}")
        else:
            # Сохраняем ключ для after_response
            kwargs["__cache_key__"] = cache_key
            logger.debug(f"Cache MISS for {method} {url}")

        return kwargs

    async def after_response(self, response):
        """
        Сохраняем успешные ответы в кэш.

        Кэшируем только статусы 200-299.
        """
        # Проверяем был ли это cacheable запрос
        if not hasattr(response, 'request'):
            return response

        # Получаем cache_key из request (если есть)
        cache_key = getattr(response.request, '__cache_key__', None)
        if cache_key is None:
            return response

        # Кэшируем только успешные ответы
        if 200 <= response.status_code < 300:
            await self._put_to_cache(cache_key, response)
            logger.debug(f"Cached response for {response.url}")

        return response

    async def on_error(self, error: Exception, **kwargs: Any) -> None:
        """Ошибки не обрабатываем."""
        pass

    async def get_stats(self) -> Dict[str, Any]:
        """
        Получить статистику кэша.

        Returns:
            Dict с hits, misses, hit_rate, size
        """
        async with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0.0

            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
                "size": len(self.cache),
                "max_size": self.max_size,
            }

    async def clear(self) -> None:
        """Очистить весь кэш."""
        async with self._lock:
            self.cache.clear()
            self._hits = 0
            self._misses = 0
            logger.info("Cache cleared")
