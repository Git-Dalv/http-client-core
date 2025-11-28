# src/http_client/core/http_client.py

import requests
from requests.exceptions import RequestException
from typing import Any, Dict, List, Optional
from ..plugins.plugin import Plugin
from .error_handler import ErrorHandler

class HTTPClient:
    def __init__(self, base_url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 10):
        self.base_url = base_url
        self.headers = headers if headers else {}
        self.timeout = timeout
        self.plugins: List[Plugin] = []
        self.error_handler = ErrorHandler()

    def add_plugin(self, plugin: Plugin):
        """Добавить плагин к клиенту"""
        self.plugins.append(plugin)

    def remove_plugin(self, plugin: Plugin):
        """Удалить плагин из клиента"""
        if plugin in self.plugins:
            self.plugins.remove(plugin)

    def _execute_before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        """Выполнить before_request для всех плагинов"""
        for plugin in self.plugins:
            kwargs = plugin.before_request(method, url, **kwargs)
        return kwargs

    def _execute_after_response(self, response: requests.Response) -> requests.Response:
        """Выполнить after_response для всех плагинов"""
        for plugin in self.plugins:
            response = plugin.after_response(response)
        return response

    def _execute_on_error(self, error: Exception):
        """Выполнить on_error для всех плагинов"""
        for plugin in self.plugins:
            plugin.on_error(error)

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> requests.Response:
        url = f"{self.base_url}{endpoint}"

        try:
            # Выполняем before_request хуки
            kwargs = self._execute_before_request(method, url, **kwargs)

            # Выполняем запрос
            response = requests.request(
                method,
                url,
                headers=self.headers,
                timeout=self.timeout,
                **kwargs
            )

            # Проверяем статус код
            response.raise_for_status()

            # Выполняем after_response хуки
            response = self._execute_after_response(response)

            return response

        except RequestException as e:
            # Выполняем on_error хуки
            self._execute_on_error(e)

            # Обрабатываем ошибку через ErrorHandler
            self.error_handler.handle_request_exception(e, url, self.timeout)

    def get(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """GET запрос"""
        return self._request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """POST запрос"""
        return self._request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """PUT запрос"""
        return self._request("PUT", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """DELETE запрос"""
        return self._request("DELETE", endpoint, **kwargs)

    def patch(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """PATCH запрос"""
        return self._request("PATCH", endpoint, **kwargs)

    def set_header(self, key: str, value: str):
        """Установить заголовок"""
        self.headers[key] = value

    def remove_header(self, key: str):
        """Удалить заголовок"""
        if key in self.headers:
            del self.headers[key]