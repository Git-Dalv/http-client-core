# src/http_client/plugins/disk_cache_plugin.py
import hashlib
import json
from typing import Any, Dict, Optional

import requests
from diskcache import Cache

from .plugin import Plugin


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
        self.cache_methods = cache_methods
        self.include_headers = include_headers

        actual_size_limit = size_limit if size_limit is not None else 2**30  # 1 GB по умолчанию

        # Инициализируем кэш
        self.cache = Cache(
            directory=cache_dir, size_limit=actual_size_limit, eviction_policy="least-recently-used"
        )

        # Статистика
        self.stats = {"hits": 0, "misses": 0, "sets": 0}

    def _generate_cache_key(self, method: str, url: str, **kwargs: Any) -> str:
        """
        Генерирует уникальный ключ для кэширования.

        Args:
            method: HTTP метод
            url: URL запроса
            **kwargs: Дополнительные параметры запроса

        Returns:
            Хеш-ключ для кэша
        """
        # Базовые компоненты ключа
        key_parts = [method.upper(), url]

        # Добавляем query параметры
        if "params" in kwargs and kwargs["params"]:
            params_str = json.dumps(kwargs["params"], sort_keys=True)
            key_parts.append(f"params:{params_str}")

        # Добавляем body для POST/PUT/PATCH
        if method.upper() in ("POST", "PUT", "PATCH"):
            if "json" in kwargs and kwargs["json"]:
                json_str = json.dumps(kwargs["json"], sort_keys=True)
                key_parts.append(f"json:{json_str}")
            elif "data" in kwargs and kwargs["data"]:
                data_str = str(kwargs["data"])
                key_parts.append(f"data:{data_str}")

        # Добавляем заголовки если требуется
        if self.include_headers and "headers" in kwargs and kwargs["headers"]:
            headers_str = json.dumps(kwargs["headers"], sort_keys=True)
            key_parts.append(f"headers:{headers_str}")

        # Генерируем хеш
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()

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
        if method.upper() not in self.cache_methods:
            return False

        # Проверяем статус код (кэшируем только успешные ответы)
        if not (200 <= response.status_code < 300):
            return False

        # Проверяем Cache-Control заголовок
        cache_control = response.headers.get("Cache-Control", "")
        if "no-store" in cache_control or "no-cache" in cache_control:
            return False

        return True

    def _serialize_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Сериализует ответ для сохранения в кэш.

        Args:
            response: Объект ответа

        Returns:
            Словарь с данными ответа
        """
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content": response.content,
            "url": response.url,
            "encoding": response.encoding,
        }

    def _deserialize_response(self, cached_data: Dict[str, Any]) -> requests.Response:
        """
        Восстанавливает объект Response из кэша.

        Args:
            cached_data: Закэшированные данные

        Returns:
            Объект Response
        """
        response = requests.Response()
        response.status_code = cached_data["status_code"]
        response.headers.update(cached_data["headers"])
        response._content = cached_data["content"]
        response.url = cached_data["url"]
        response.encoding = cached_data["encoding"]

        # Добавляем маркер что ответ из кэша
        response.headers["X-Cache"] = "HIT"

        return response

    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Проверяет наличие закэшированного ответа перед запросом.

        Args:
            method: HTTP метод
            url: URL запроса
            **kwargs: Параметры запроса

        Returns:
            Обновленные параметры запроса
        """
        # Проверяем, нужно ли кэшировать этот метод
        if method.upper() not in self.cache_methods:
            return kwargs

        # Генерируем ключ кэша
        cache_key = self._generate_cache_key(method, url, **kwargs)

        # Проверяем наличие в кэше
        cached_data = self.cache.get(cache_key)

        if cached_data is not None:
            # Кэш найден
            self.stats["hits"] += 1

            # Сохраняем закэшированный ответ в kwargs для использования
            kwargs["_cached_response"] = self._deserialize_response(cached_data)
            kwargs["_cache_key"] = cache_key
        else:
            # Кэш не найден
            self.stats["misses"] += 1
            kwargs["_cache_key"] = cache_key

        return kwargs

    def after_response(self, response: requests.Response) -> requests.Response:
        """
        Сохраняет ответ в кэш после получения.

        Args:
            response: Объект ответа

        Returns:
            Объект ответа
        """
        # Проверяем, есть ли закэшированный ответ в request
        if hasattr(response, "request") and hasattr(response.request, "_cached_response"):
            # Возвращаем закэшированный ответ
            cached_response = response.request._cached_response
            # Копируем request для сохранения контекста
            cached_response.request = response.request
            return cached_response

        # Проверяем, нужно ли кэшировать ответ
        if hasattr(response, "request"):
            method = response.request.method

            if self._should_cache(method, response):
                # Получаем ключ кэша из request
                cache_key = getattr(response.request, "_cache_key", None)

                if cache_key:
                    # Сериализуем и сохраняем ответ
                    serialized = self._serialize_response(response)
                    self.cache.set(cache_key, serialized, expire=self.ttl)
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
        self.stats = {"hits": 0, "misses": 0, "sets": 0}

    def delete(self, method: str, url: str, **kwargs: Any):
        """
        Удаляет конкретную запись из кэша.

        Args:
            method: HTTP метод
            url: URL запроса
            **kwargs: Параметры запроса
        """
        cache_key = self._generate_cache_key(method, url, **kwargs)
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
            "sets": self.stats["sets"],
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
