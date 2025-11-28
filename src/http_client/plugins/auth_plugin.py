# src/http_client/plugins/auth_plugin.py

from typing import Any, Dict, Optional
import requests
from .plugin import Plugin

class AuthPlugin(Plugin):
    """Плагин для различных типов аутентификации"""

    def __init__(self, auth_type: str = "bearer", token: Optional[str] = None,
                 username: Optional[str] = None, password: Optional[str] = None):
        """
        Args:
            auth_type: Тип аутентификации ('bearer', 'basic', 'api_key')
            token: Токен для Bearer или API Key аутентификации
            username: Имя пользователя для Basic аутентификации
            password: Пароль для Basic аутентификации
        """
        self.auth_type = auth_type.lower()
        self.token = token
        self.username = username
        self.password = password

    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        """Добавляет заголовки аутентификации"""
        if 'headers' not in kwargs:
            kwargs['headers'] = {}

        if self.auth_type == 'bearer' and self.token:
            kwargs['headers']['Authorization'] = f"Bearer {self.token}"

        elif self.auth_type == 'api_key' and self.token:
            kwargs['headers']['X-API-Key'] = self.token

        elif self.auth_type == 'basic' and self.username and self.password:
            # requests поддерживает Basic auth через параметр auth
            kwargs['auth'] = (self.username, self.password)

        return kwargs

    def after_response(self, response: requests.Response) -> requests.Response:
        """Обработка после получения ответа"""
        return response

    def on_error(self, error: Exception) -> None:
        """Обработка ошибок"""
        pass

    def update_token(self, token: str):
        """Обновляет токен аутентификации"""
        self.token = token