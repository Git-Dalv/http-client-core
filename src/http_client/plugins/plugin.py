# src/http_client/plugins/plugin.py

from abc import ABC, abstractmethod
from typing import Any, Dict

import requests


class Plugin(ABC):
    """Базовый класс для всех плагинов"""

    @abstractmethod
    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        """Вызывается перед отправкой запроса"""
        pass

    @abstractmethod
    def after_response(self, response: requests.Response) -> requests.Response:
        """Вызывается после получения ответа"""
        pass

    @abstractmethod
    def on_error(self, error: Exception, **kwargs: Any) -> None:
        """Вызывается при возникновении ошибки"""
        pass
