# src/http_client/plugins/disk_cache_plugin.py
import hashlib
import json
import time
from typing import Any, Dict, Optional

import requests
from diskcache import Cache

from .plugin import Plugin
from ..utils.serialization import serialize_response, deserialize_response


class DiskCachePlugin(Plugin):
    """
    Плагин для кэширования HTTP ответов на диске.

    Features:
        - Персистентное хранение кэша между запусками приложения
        - Настраиваемое время жизни кэша (TTL)
        - Автоматическая очистка устаревших записей
        - Поддержка различных HTTP методов
        - Кэширование на основе URL, метода и параметров
        - Ограничение размера кэша

    Example:
        >>> from http_client import HTTPClient
        >>> from http_client.plugins import DiskCachePlugin
        >>>
        >>> client = HTTPClient(base_url="https://api.example.com")
        >>> client.add_plugin(DiskCachePlugin(
        ...     cache_dir=".cache",
        ...     ttl=3600,  # 1 час
        ...     size_limit=1024 * 1024 * 100  # 100 MB
        ... ))
        >>>
        >>> # Первый запрос - идет на сервер
        >>> response1 = client.get("/data")
        >>>
        >>> # Второй запрос - берется из кэша
        >>> response2 = client.get("/data")
    """

    def __init__(
        self,
        cache_dir: str = ".http_cache",
        ttl: int = 3600,
        size_limit: Optional[int] = None,
        cache_methods: tuple = ("GET",),
        include_headers: bool = False,
    ):
        """
        Инициализация плагина кэширования на диске.

        Args:
            cache_dir: Директория для хранения кэша
            ttl: Время жизни кэша в секундах (по умолчанию 1 час)
            size_limit: Максимальный размер кэша в байтах (None = без ограничений)
            cache_methods: Кортеж HTTP методов для кэширования
            include_headers: Учитывать заголовки при генерации ключа кэша
        """
        self.cache_dir = cache_dir
        self.ttl = ttl
        self.size_limit = size_limit
        self.cacheable_methods = [m.upper() for m in cache_methods]  # Normalize to uppercase
        self.include_headers = include_headers

        actual_size_limit = size_limit if size_limit is not None else 2**30  # 1 GB по умолчанию

        # Инициализируем кэш
        self.cache = Cache(
            directory=cache_dir, size_limit=actual_size_limit, eviction_policy="least-recently-used"
        )

        # Статистика
        self.stats = {"hits": 0, "misses": 0}

    def _generate_cache_key(self, method: str, url: str, kwargs: Dict[str, Any]) -> str:
        """
        Генерирует стабильный ключ кэша из параметров запроса.

        Args:
            method: HTTP метод
            url: URL запроса
            kwargs: Параметры запроса (params, headers, etc.)

        Returns:
            SHA256 хеш как ключ кэша
        """
        # Извлекаем релевантные части
        params = kwargs.get('params', {})

        # Стабильная сериализация (sorted keys)
        params_str = json.dumps(params, sort_keys=True) if params else ''

        # Генерируем ключ
        key_source = f"{method.upper()}:{url}:{params_str}"

        return hashlib.sha256(key_source.encode('utf-8')).hexdigest()

    def _should_cache(self, method: str, response: requests.Response) -> bool:
        """
        Определяет, нужно ли кэшировать ответ.

        Args:
            method: HTTP метод
            response: Объект ответа

        Returns:
            True если ответ нужно кэшировать
        """
        # Проверяем метод
        if method.upper() not in self.cacheable_methods:
            return False

        # Проверяем статус код (кэшируем только успешные ответы)
        if not (200 <= response.status_code < 300):
            return False

        # Проверяем Cache-Control заголовок
        cache_control = response.headers.get("Cache-Control", "")
        if "no-store" in cache_control or "no-cache" in cache_control:
            return False

        return True

    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Проверяет наличие закэшированного ответа перед запросом.

        Args:
            method: HTTP метод
            url: URL запроса
            **kwargs: Параметры запроса

        Returns:
            Словарь с ключом '__cached_response__' если найден кэш,
            иначе пустой словарь (kwargs не модифицируются)
        """
        # Проверяем, нужно ли кэшировать этот метод
        if method.upper() not in self.cacheable_methods:
            return {}

        # Генерируем ключ кэша
        cache_key = self._generate_cache_key(method, url, kwargs)

        # Проверяем наличие в кэше
        cached_data = self.cache.get(cache_key)

        if cached_data is not None:
            # Кэш найден - восстанавливаем ответ
            self.stats["hits"] += 1

            # Используем утилиты для десериализации
            cached_response = deserialize_response(cached_data)

            # Добавляем маркер что ответ из кэша
            cached_response.headers["X-Cache"] = "HIT"

            # Возвращаем специальный ключ для short-circuit
            return {"__cached_response__": cached_response}
        else:
            # Кэш не найден
            self.stats["misses"] += 1
            return {}

    def after_response(self, response: requests.Response) -> requests.Response:
        """
        Сохраняет ответ в кэш после получения.

        Args:
            response: Объект ответа

        Returns:
            Объект ответа
        """
        # Lazy import to avoid circular dependency
        from ..core.http_client import get_current_request_context

        # Получаем контекст текущего запроса (thread-safe)
        context = get_current_request_context()

        # Если контекста нет, ничего не делаем
        if not context:
            return response

        method = context.get("method")
        url = context.get("url")
        kwargs = context.get("kwargs", {})

        # Проверяем, нужно ли кэшировать ответ
        if self._should_cache(method, response):
            # Генерируем ключ кэша из параметров запроса
            cache_key = self._generate_cache_key(method, url, kwargs)

            # Сериализуем и сохраняем ответ
            serialized = serialize_response(response)
            self.cache.set(cache_key, serialized, expire=self.ttl)

            # Обновляем статистику (инициализируем "sets" если нет)
            if "sets" not in self.stats:
                self.stats["sets"] = 0
            self.stats["sets"] += 1

            # Добавляем маркер что ответ был закэширован
            response.headers["X-Cache"] = "MISS"

        return response

    def close(self):
        """Закрывает соединение с кэшем и освобождает ресурсы"""
        if hasattr(self, "cache"):
            self.cache.close()

    def on_error(self, error: Exception, **kwargs) -> bool:
        """
        Обработка ошибок.
        При ошибке не делаем ничего особенного.

        Args:
            error: Возникшее исключение
            **kwargs: Дополнительные параметры

        Returns:
            False - не повторять запрос
        """
        # При ошибке мы не кэшируем ответ
        # Можно добавить логирование если нужно
        return False

    def clear(self):
        """Очищает весь кэш"""
        self.cache.clear()
        self.stats = {"hits": 0, "misses": 0}

    def delete(self, method: str, url: str, **kwargs: Any):
        """
        Удаляет конкретную запись из кэша.

        Args:
            method: HTTP метод
            url: URL запроса
            **kwargs: Параметры запроса
        """
        cache_key = self._generate_cache_key(method, url, kwargs)
        self.cache.delete(cache_key)

    def get_stats(self) -> Dict[str, Any]:
        """
        Получает статистику использования кэша.

        Returns:
            Словарь со статистикой
        """
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "sets": self.stats.get("sets", 0),
            "hit_rate": f"{hit_rate:.2f}%",
            "cache_size": len(self.cache),
            "disk_size_bytes": self.cache.volume(),
        }

    def get_size(self) -> int:
        """
        Получает текущий размер кэша на диске в байтах.

        Returns:
            Размер в байтах
        """
        return self.cache.volume()

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"DiskCachePlugin(cache_dir='{self.cache_dir}', ttl={self.ttl}, "
            f"hits={stats['hits']}, misses={stats['misses']}, "
            f"hit_rate={stats['hit_rate']})"
        )
