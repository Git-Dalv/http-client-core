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
    HTTPError,
    TimeoutError,
    ConnectionError,
    ServerError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    TooManyRequestsError,
    TooManyRetriesError,
    ResponseTooLargeError,
    CircuitOpenError,
)
from .core.retry_engine import RetryEngine
from .core.circuit_breaker import AsyncCircuitBreaker
from .plugins.plugin import Plugin
from .plugins.async_plugin import AsyncPlugin


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

        # Initialize plugins and sort by priority (lower = earlier execution)
        plugin_list = list(plugins) if plugins else []
        plugin_list.sort(key=lambda p: getattr(p, 'priority', 50))  # Default priority = 50 (NORMAL)
        self._plugins: List[Plugin] = plugin_list

        self._proxies = proxies
        self._retry_engine = RetryEngine(self._config.retry)

        # Circuit breaker for fault tolerance
        self._circuit_breaker = AsyncCircuitBreaker(self._config.circuit_breaker)

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
            CircuitOpenError: Circuit breaker is OPEN - too many failures
            TooManyRetriesError: Превышено количество попыток
            TimeoutError: Таймаут запроса
            ConnectionError: Ошибка соединения
        """
        # Check circuit breaker before starting
        if not await self._circuit_breaker.can_execute():
            # Circuit is open - block request
            stats = await self._circuit_breaker.get_stats()
            raise CircuitOpenError(
                "Circuit breaker is OPEN - too many failures",
                url=url,
                recovery_time=stats.get('last_failure_time', 0) + self._config.circuit_breaker.recovery_timeout if stats.get('last_failure_time') else None,
                failure_count=stats.get('failure_count', 0)
            )

        client = await self._get_client()

        # Создаём RetryEngine для этого запроса (для thread-safety в async)
        retry_engine = RetryEngine(self._config.retry)

        # Выполняем before_request хуки плагинов
        for plugin in self._plugins:
            try:
                # Проверяем тип плагина
                if isinstance(plugin, AsyncPlugin):
                    # Async плагин - вызываем напрямую
                    result = await plugin.before_request(method, url, **kwargs)
                else:
                    # Sync плагин - выполняем в executor чтобы не блокировать event loop
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None,
                        lambda: plugin.before_request(method, url, **kwargs)
                    )

                if isinstance(result, dict):
                    kwargs.update(result)
            except Exception as e:
                warnings.warn(f"Plugin {plugin.__class__.__name__} error in before_request: {e}")

        last_error: Optional[Exception] = None
        response_for_retry: Optional[httpx.Response] = None

        while True:
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

                # Проверяем статус код
                if response.status_code >= 400:
                    # Создаём ServerError для проверки retry
                    if response.status_code >= 500:
                        error = ServerError(response.status_code, str(response.url))
                        response_for_retry = response

                        # Проверяем нужен ли retry
                        if retry_engine.should_retry(method, error, response):
                            # Retry
                            await retry_engine.async_wait(error, response)
                            retry_engine.increment()
                            continue
                        else:
                            # Не ретраим - raise
                            raise error
                    else:
                        # 4xx - не ретраим
                        response.raise_for_status()

                # Успешный ответ
                retry_engine.reset()

                # Record success in circuit breaker
                await self._circuit_breaker.record_success()

                # Выполняем after_response хуки
                for plugin in self._plugins:
                    try:
                        if isinstance(plugin, AsyncPlugin):
                            # Async плагин
                            response = await plugin.after_response(response)
                        else:
                            # Sync плагин - выполняем в executor
                            loop = asyncio.get_event_loop()
                            response = await loop.run_in_executor(
                                None,
                                lambda: plugin.after_response(response)
                            )
                    except Exception as e:
                        warnings.warn(f"Plugin {plugin.__class__.__name__} error in after_response: {e}")

                return response

            except httpx.TimeoutException as e:
                last_error = TimeoutError(str(e), url)
            except httpx.ConnectError as e:
                last_error = ConnectionError(str(e), url)
            except httpx.HTTPStatusError as e:
                # Конвертируем в наш тип исключения по статус коду
                status_code = e.response.status_code
                response_url = str(e.response.url)
                response_for_retry = e.response

                if status_code == 400:
                    last_error = BadRequestError(response_url)
                elif status_code == 401:
                    last_error = UnauthorizedError(response_url)
                elif status_code == 403:
                    last_error = ForbiddenError(response_url)
                elif status_code == 404:
                    last_error = NotFoundError(response_url)
                elif status_code == 429:
                    retry_after = e.response.headers.get('Retry-After')
                    last_error = TooManyRequestsError(response_url, retry_after=retry_after)
                elif 400 <= status_code < 500:
                    # Другие 4xx ошибки
                    last_error = HTTPError(status_code, response_url)
                else:
                    # 5xx ошибки
                    last_error = ServerError(status_code, response_url)
            except ResponseTooLargeError:
                raise
            except ServerError:
                # Уже обработано выше, просто пробрасываем
                raise
            except Exception as e:
                last_error = HTTPClientException(str(e))

            # Выполняем on_error хуки
            for plugin in self._plugins:
                try:
                    if isinstance(plugin, AsyncPlugin):
                        # Async плагин
                        await plugin.on_error(last_error, method=method, url=url)
                    else:
                        # Sync плагин - выполняем в executor
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(
                            None,
                            lambda: plugin.on_error(last_error, method=method, url=url)
                        )
                except Exception:
                    pass

            # Проверяем нужен ли retry
            if not retry_engine.should_retry(method, last_error, response_for_retry):
                # Record failure in circuit breaker (final failure, no more retries)
                await self._circuit_breaker.record_failure(last_error)

                # Проверяем достигли ли max attempts
                is_max_attempts = retry_engine.attempt + 1 >= self._config.retry.max_attempts

                if is_max_attempts:
                    raise TooManyRetriesError(
                        max_retries=self._config.retry.max_attempts - 1,
                        last_error=last_error,
                        url=url,
                    )
                else:
                    # Фатальная ошибка или non-idempotent метод
                    raise last_error

            # Ждём и повторяем
            await retry_engine.async_wait(last_error, response_for_retry)
            retry_engine.increment()

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

    # ==================== File Download ====================

    async def download(
        self,
        url: str,
        file_path: str,
        chunk_size: int = 8192,
        progress_callback: Optional[callable] = None,
        **kwargs
    ) -> int:
        """
        Асинхронная загрузка большого файла с streaming для избежания проблем с памятью.

        Args:
            url: URL для загрузки
            file_path: Путь для сохранения файла
            chunk_size: Размер chunk для загрузки (по умолчанию 8KB)
            progress_callback: Опциональный callback(downloaded_bytes, total_bytes)
                              для отслеживания прогресса
            **kwargs: Дополнительные параметры запроса

        Returns:
            Всего байт загружено

        Raises:
            ResponseTooLargeError: Если размер файла превышает максимально допустимый
            HTTPError: При ошибках HTTP
            IOError: При ошибках записи файла

        Example:
            >>> async with AsyncHTTPClient(base_url="https://example.com") as client:
            ...     # Простая загрузка
            ...     bytes_downloaded = await client.download("/large-file.zip", "output.zip")
            ...     print(f"Downloaded {bytes_downloaded} bytes")
            ...
            ...     # С callback для прогресса
            ...     def on_progress(downloaded, total):
            ...         if total > 0:
            ...             percent = (downloaded / total) * 100
            ...             print(f"Progress: {percent:.1f}%")
            ...
            ...     await client.download("/file.zip", "output.zip", progress_callback=on_progress)
        """
        import os

        # Check if aiofiles is available
        try:
            import aiofiles
            use_aiofiles = True
        except ImportError:
            use_aiofiles = False
            warnings.warn(
                "aiofiles not installed. File I/O will block the event loop. "
                "Install with: pip install aiofiles",
                stacklevel=2
            )

        client = await self._get_client()
        downloaded = 0
        max_size = self._config.security.max_response_size

        try:
            # Используем streaming response
            async with client.stream("GET", url, **kwargs) as response:
                response.raise_for_status()

                # Получаем общий размер если доступен
                total_size = int(response.headers.get('Content-Length', 0))

                # Проверяем размер до начала загрузки
                if total_size > 0 and total_size > max_size:
                    raise ResponseTooLargeError(
                        f"File size ({total_size} bytes) exceeds maximum "
                        f"({max_size} bytes)",
                        url=str(response.url),
                        size=total_size,
                        max_size=max_size
                    )

                # Загружаем файл chunk по chunk
                if use_aiofiles:
                    # Async file I/O
                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in response.aiter_bytes(chunk_size):
                            if chunk:  # Фильтруем keep-alive chunks
                                # Проверяем размер ПЕРЕД записью для предотвращения переполнения диска
                                downloaded += len(chunk)
                                if downloaded > max_size:
                                    raise ResponseTooLargeError(
                                        f"Downloaded size ({downloaded} bytes) exceeds maximum "
                                        f"({max_size} bytes)",
                                        url=str(response.url),
                                        size=downloaded,
                                        max_size=max_size
                                    )

                                await f.write(chunk)

                                if progress_callback:
                                    progress_callback(downloaded, total_size)
                else:
                    # Sync file I/O (блокирует event loop, но без доп. зависимостей)
                    with open(file_path, 'wb') as f:
                        async for chunk in response.aiter_bytes(chunk_size):
                            if chunk:
                                downloaded += len(chunk)
                                if downloaded > max_size:
                                    raise ResponseTooLargeError(
                                        f"Downloaded size ({downloaded} bytes) exceeds maximum "
                                        f"({max_size} bytes)",
                                        url=str(response.url),
                                        size=downloaded,
                                        max_size=max_size
                                    )

                                f.write(chunk)

                                if progress_callback:
                                    progress_callback(downloaded, total_size)

            return downloaded

        except Exception as e:
            # Очищаем частично загруженный файл при ошибке
            if os.path.exists(file_path):
                os.remove(file_path)
            raise

    # ==================== Плагины ====================

    def add_plugin(self, plugin: Plugin) -> None:
        """
        Добавляет плагин к клиенту и сортирует плагины по приоритету.

        Плагины выполняются в порядке приоритета (меньше = раньше).
        По умолчанию плагины без явного приоритета получают NORMAL (50).

        Args:
            plugin: Экземпляр плагина (Plugin или AsyncPlugin)
        """
        self._plugins.append(plugin)
        # Sort plugins by priority (lower = earlier execution)
        # Stable sort preserves order for equal priorities
        self._plugins.sort(key=lambda p: getattr(p, 'priority', 50))

    def remove_plugin(self, plugin: Plugin) -> None:
        """Удалить плагин."""
        if plugin in self._plugins:
            self._plugins.remove(plugin)

    def get_plugins_order(self) -> List[tuple]:
        """
        Возвращает список плагинов в порядке выполнения для отладки.

        Полезно для проверки правильности порядка выполнения плагинов.

        Returns:
            List[tuple]: Список кортежей (имя_плагина, приоритет)

        Example:
            >>> client = AsyncHTTPClient()
            >>> client.add_plugin(AsyncCachePlugin())
            >>> client.add_plugin(AsyncRateLimitPlugin())
            >>> client.add_plugin(AsyncMonitoringPlugin())
            >>> print(client.get_plugins_order())
            [('AsyncCachePlugin', 10), ('AsyncRateLimitPlugin', 25), ('AsyncMonitoringPlugin', 100)]
        """
        return [(p.__class__.__name__, getattr(p, 'priority', 50)) for p in self._plugins]

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
