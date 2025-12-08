# src/http_client/plugins/plugin.py

from abc import ABC, abstractmethod
from typing import Any, Dict

import requests


class PluginPriority:
    """
    Константы приоритетов для плагинов.

    Плагины с меньшим приоритетом выполняются раньше.
    Используйте эти константы для установки правильного порядка выполнения.

    Example:
        >>> class MyAuthPlugin(Plugin):
        ...     priority = PluginPriority.FIRST  # Выполнится первым
        ...
        >>> class MyLoggingPlugin(Plugin):
        ...     priority = PluginPriority.LAST  # Выполнится последним
    """
    FIRST = 0       # Выполняется первым (Auth, Headers, Browser Fingerprint)
    CACHE = 10      # Специально для Cache (должен быть рано, но после Auth)
    HIGH = 25       # Высокий приоритет (Rate Limiting)
    NORMAL = 50     # Обычный приоритет (по умолчанию для кастомных плагинов)
    LOW = 75        # Низкий приоритет
    LAST = 100      # Выполняется последним (Logging, Monitoring)


class Plugin(ABC):
    """
    Базовый класс для всех плагинов.

    Attributes:
        priority: Приоритет выполнения плагина (меньше = раньше).
                 По умолчанию NORMAL (50). Используйте PluginPriority константы.
    """

    # Class attribute для приоритета (можно переопределить в подклассах)
    priority: int = PluginPriority.NORMAL

    @abstractmethod
    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        """Вызывается перед отправкой запроса"""
        pass

    @abstractmethod
    def after_response(self, response: requests.Response) -> requests.Response:
        """Вызывается после получения ответа"""
        pass

    @abstractmethod
    def on_error(self, error: Exception, **kwargs: Any) -> bool:
        """
        Вызывается при возникновении ошибки.

        Returns:
            True если плагин хочет повторить запрос (retry)
            False если исключение должно быть выброшено
        """
        pass
