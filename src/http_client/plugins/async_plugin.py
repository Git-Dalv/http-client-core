# src/http_client/plugins/async_plugin.py
"""
Базовый класс для асинхронных плагинов.

Async плагины используются в AsyncHTTPClient для неблокирующих операций.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

try:
    import httpx
except ImportError:
    httpx = None

from .plugin import PluginPriority


class AsyncPlugin(ABC):
    """
    Базовый класс для асинхронных плагинов.

    Async плагины выполняют операции асинхронно, не блокируя event loop.
    Используются в AsyncHTTPClient.

    Attributes:
        priority: Приоритет выполнения плагина (меньше = раньше).
                 По умолчанию NORMAL (50). Используйте PluginPriority константы.

    Example:
        >>> class MyAsyncPlugin(AsyncPlugin):
        ...     priority = PluginPriority.HIGH  # Выполнится рано
        ...
        ...     async def before_request(self, method, url, **kwargs):
        ...         await asyncio.sleep(0.1)  # async операция
        ...         return kwargs
        ...
        ...     async def after_response(self, response):
        ...         return response
        ...
        ...     async def on_error(self, error, **kwargs):
        ...         pass
    """

    # Class attribute для приоритета (можно переопределить в подклассах)
    priority: int = PluginPriority.NORMAL

    async def before_request(
        self,
        method: str,
        url: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Вызывается перед отправкой запроса (async).

        Args:
            method: HTTP метод (GET, POST, etc.)
            url: URL запроса
            **kwargs: Параметры запроса

        Returns:
            Модифицированные kwargs (или оригинальные)

        Example:
            >>> async def before_request(self, method, url, **kwargs):
            ...     kwargs['headers'] = kwargs.get('headers', {})
            ...     kwargs['headers']['X-Custom'] = 'value'
            ...     return kwargs
        """
        return kwargs

    async def after_response(
        self,
        response
    ):
        """
        Вызывается после получения ответа (async).

        Args:
            response: httpx.Response объект

        Returns:
            Response объект (оригинальный или модифицированный)

        Example:
            >>> async def after_response(self, response):
            ...     await log_response(response)
            ...     return response
        """
        return response

    async def on_error(
        self,
        error: Exception,
        **kwargs: Any
    ) -> None:
        """
        Вызывается при возникновении ошибки (async).

        Args:
            error: Исключение
            **kwargs: Дополнительная информация (method, url, etc.)

        Example:
            >>> async def on_error(self, error, **kwargs):
            ...     await log_error(error, kwargs.get('url'))
        """
        pass


class SyncPluginAdapter(AsyncPlugin):
    """
    Адаптер для использования sync плагинов в async контексте.

    Оборачивает sync плагин и выполняет его методы в thread pool,
    чтобы не блокировать event loop.

    Example:
        >>> from .plugin import Plugin
        >>> sync_plugin = MySyncPlugin()
        >>> async_plugin = SyncPluginAdapter(sync_plugin)
        >>> # Теперь можно использовать в AsyncHTTPClient
    """

    def __init__(self, sync_plugin):
        """
        Args:
            sync_plugin: Sync плагин (Plugin instance)
        """
        self._sync_plugin = sync_plugin

    async def before_request(
        self,
        method: str,
        url: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Выполнить sync before_request в thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._sync_plugin.before_request(method, url, **kwargs)
        )

    async def after_response(self, response):
        """Выполнить sync after_response в thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._sync_plugin.after_response(response)
        )

    async def on_error(
        self,
        error: Exception,
        **kwargs: Any
    ) -> None:
        """Выполнить sync on_error в thread pool."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._sync_plugin.on_error(error, **kwargs)
        )

    def __repr__(self):
        """Представление адаптера."""
        return f"SyncPluginAdapter({self._sync_plugin!r})"
