# src/http_client/async_client.py
"""
Асинхронный HTTP клиент на базе httpx.

Предоставляет async/await API для использования в asyncio приложениях
(FastAPI, aiohttp, etc.)
"""

import asyncio
import time
import warnings
from typing import Any, Dict, List, Optional, Union

try:
    import httpx
except ImportError:
    raise ImportError(
        "httpx is required for AsyncHTTPClient. "
        "Install with: pip install http-client-core[async]"
    )

from .core.config import HTTPClientConfig, TimeoutConfig
from .core.exceptions import (
    HTTPClientException,
    TimeoutError,
    ConnectionError,
    ServerError,
    TooManyRetriesError,
    ResponseTooLargeError,
)
from .plugins.plugin import Plugin


class AsyncHTTPClient:
    """
    Асинхронный HTTP клиент с поддержкой retry, плагинов и таймаутов.

    Построен на httpx для полной async/await поддержки.

    Example:
        >>> async with AsyncHTTPClient(base_url="https://api.example.com") as client:
        ...     response = await client.get("/users")
        ...     print(response.json())

        >>> # Или без context manager
        >>> client = AsyncHTTPClient(base_url="https://api.example.com")
        >>> response = await client.get("/users")
        >>> await client.close()

    Features:
        - Полная async/await поддержка
        - Автоматические retry с exponential backoff
        - Connection pooling
        - Таймауты (connect, read, total)
        - Совместимость с sync плагинами (adapter)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        *,
        config: Optional[HTTPClientConfig] = None,
        timeout: Union[int, float, TimeoutConfig] = 30,
        max_retries: int = 3,
        headers: Optional[Dict[str, str]] = None,
        verify_ssl: bool = True,
        proxies: Optional[Dict[str, str]] = None,
        plugins: Optional[List[Plugin]] = None,
        **kwargs,
    ):
        """
        Инициализация асинхронного клиента.

        Args:
            base_url: Базовый URL для всех запросов
            config: HTTPClientConfig объект (если указан, остальные параметры игнорируются)
            timeout: Таймаут в секундах или TimeoutConfig
            max_retries: Максимальное количество повторных попыток
            headers: Заголовки по умолчанию
            verify_ssl: Проверять SSL сертификаты
            proxies: Прокси серверы {"http://": "...", "https://": "..."}
            plugins: Список плагинов
        """
        # Создаём конфиг
        if config is not None:
            self._config = config
        else:
            self._config = HTTPClientConfig.create(
                base_url=base_url,
                timeout=timeout,
                max_retries=max_retries,
                headers=headers,
                verify_ssl=verify_ssl,
                **kwargs,
            )

        self._base_url = self._config.base_url
        self._plugins: List[Plugin] = list(plugins) if plugins else []
        self._proxies = proxies

        # Создаём httpx timeout
        if isinstance(timeout, TimeoutConfig):
            self._timeout = httpx.Timeout(
                connect=timeout.connect,
                read=timeout.read,
                write=timeout.read,  # Используем read для write
                pool=timeout.total,
            )
        else:
            self._timeout = httpx.Timeout(timeout)

        # Клиент создаётся лениво или при входе в context manager
        self._client: Optional[httpx.AsyncClient] = None
        self._owns_client = True

    async def _get_client(self) -> httpx.AsyncClient:
        """Получить или создать httpx клиент."""
        if self._client is None:
            # Создаём kwargs для httpx.AsyncClient
            client_kwargs = {
                "base_url": self._base_url or "",
                "timeout": self._timeout,
                "verify": self._config.security.verify_ssl,
                "headers": self._config.headers,
                "limits": httpx.Limits(
                    max_connections=self._config.pool.pool_maxsize,
                    max_keepalive_connections=self._config.pool.pool_connections,
                ),
                "follow_redirects": self._config.security.allow_redirects,
            }

            # Добавляем proxies только если они указаны
            if self._proxies:
                client_kwargs["proxies"] = self._proxies

            self._client = httpx.AsyncClient(**client_kwargs)
        return self._client

    async def __aenter__(self) -> "AsyncHTTPClient":
        """Async context manager entry."""
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Закрыть клиент и освободить ресурсы."""
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    # ==================== HTTP методы ====================

    async def request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Выполнить HTTP запрос с retry логикой.

        Args:
            method: HTTP метод (GET, POST, etc.)
            url: URL (относительный или абсолютный)
            **kwargs: Дополнительные параметры для httpx

        Returns:
            httpx.Response объект

        Raises:
            TooManyRetriesError: Превышено количество попыток
            TimeoutError: Таймаут запроса
            ConnectionError: Ошибка соединения
        """
        client = await self._get_client()

        # Выполняем before_request хуки плагинов
        for plugin in self._plugins:
            try:
                result = plugin.before_request(method, url, **kwargs)
                if isinstance(result, dict):
                    kwargs.update(result)
            except Exception as e:
                warnings.warn(f"Plugin {plugin.__class__.__name__} error in before_request: {e}")

        last_error: Optional[Exception] = None
        max_attempts = self._config.retry.max_attempts

        for attempt in range(max_attempts):
            try:
                response = await client.request(method, url, **kwargs)

                # Проверяем размер ответа
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > self._config.security.max_response_size:
                    raise ResponseTooLargeError(
                        f"Response size ({content_length} bytes) exceeds maximum",
                        url=str(response.url),
                        size=int(content_length),
                    )

                # Проверяем статус для retry
                if response.status_code >= 500 and attempt < max_attempts - 1:
                    # Server error - retry
                    wait_time = self._calculate_backoff(attempt)
                    await asyncio.sleep(wait_time)
                    continue

                # Выполняем after_response хуки
                for plugin in self._plugins:
                    try:
                        response = plugin.after_response(response)
                    except Exception as e:
                        warnings.warn(f"Plugin {plugin.__class__.__name__} error in after_response: {e}")

                return response

            except httpx.TimeoutException as e:
                last_error = TimeoutError(str(e), url)
            except httpx.ConnectError as e:
                last_error = ConnectionError(str(e), url)
            except httpx.HTTPStatusError as e:
                last_error = ServerError(e.response.status_code, url)
            except ResponseTooLargeError:
                raise
            except Exception as e:
                last_error = HTTPClientException(str(e))

            # Выполняем on_error хуки
            for plugin in self._plugins:
                try:
                    plugin.on_error(last_error, method=method, url=url)
                except Exception:
                    pass

            # Backoff перед retry
            if attempt < max_attempts - 1:
                wait_time = self._calculate_backoff(attempt)
                await asyncio.sleep(wait_time)

        raise TooManyRetriesError(
            max_retries=max_attempts,
            last_error=last_error,
            url=url,
        )

    def _calculate_backoff(self, attempt: int) -> float:
        """Вычислить время ожидания для retry."""
        base = self._config.retry.backoff_base
        factor = self._config.retry.backoff_factor
        max_wait = self._config.retry.backoff_max

        wait_time = base * (factor ** attempt)

        # Добавляем jitter если включено
        if self._config.retry.backoff_jitter:
            import random
            jitter = random.uniform(0.5, 1.5)
            wait_time *= jitter

        return min(wait_time, max_wait)

    # ==================== Удобные методы ====================

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """GET запрос."""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """POST запрос."""
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> httpx.Response:
        """PUT запрос."""
        return await self.request("PUT", url, **kwargs)

    async def patch(self, url: str, **kwargs) -> httpx.Response:
        """PATCH запрос."""
        return await self.request("PATCH", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """DELETE запрос."""
        return await self.request("DELETE", url, **kwargs)

    async def head(self, url: str, **kwargs) -> httpx.Response:
        """HEAD запрос."""
        return await self.request("HEAD", url, **kwargs)

    async def options(self, url: str, **kwargs) -> httpx.Response:
        """OPTIONS запрос."""
        return await self.request("OPTIONS", url, **kwargs)

    # ==================== Плагины ====================

    def add_plugin(self, plugin: Plugin) -> None:
        """Добавить плагин."""
        self._plugins.append(plugin)

    def remove_plugin(self, plugin: Plugin) -> None:
        """Удалить плагин."""
        if plugin in self._plugins:
            self._plugins.remove(plugin)

    # ==================== Health Check ====================

    async def health_check(
        self,
        test_url: Optional[str] = None,
        timeout: float = 5.0,
    ) -> Dict[str, Any]:
        """
        Асинхронная проверка здоровья клиента.

        Args:
            test_url: URL для проверки соединения
            timeout: Таймаут для тестового запроса

        Returns:
            Словарь с диагностической информацией
        """
        result = {
            "healthy": True,
            "base_url": self._base_url,
            "client_type": "async",
            "plugins_count": len(self._plugins),
            "plugins": [p.__class__.__name__ for p in self._plugins],
            "connectivity": None,
        }

        if test_url:
            connectivity = {
                "url": test_url,
                "reachable": False,
                "response_time_ms": None,
                "status_code": None,
                "error": None,
            }

            try:
                client = await self._get_client()
                start = time.time()
                response = await client.head(test_url, timeout=timeout)
                elapsed = (time.time() - start) * 1000

                connectivity["reachable"] = True
                connectivity["response_time_ms"] = round(elapsed, 2)
                connectivity["status_code"] = response.status_code

            except Exception as e:
                connectivity["error"] = str(e)[:100]
                result["healthy"] = False

            result["connectivity"] = connectivity

        return result

    # ==================== Properties ====================

    @property
    def base_url(self) -> Optional[str]:
        """Базовый URL."""
        return self._base_url
