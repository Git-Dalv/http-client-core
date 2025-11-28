# src/http_client/plugins/retry_plugin.py

import time
from typing import Any, Dict
import requests
from .plugin import Plugin

class RetryPlugin(Plugin):
    """Плагин для автоматических повторных попыток при ошибках"""

    def __init__(self, max_retries: int = 3, backoff_factor: float = 0.5):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_count = 0

    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        # Сохраняем параметры для возможных повторных попыток
        self.last_request = {'method': method, 'url': url, 'kwargs': kwargs}
        return kwargs

    def after_response(self, response: requests.Response) -> requests.Response:
        # Сбрасываем счетчик при успешном ответе
        self.retry_count = 0
        return response

    def on_error(self, error: Exception) -> None:
        self.retry_count += 1
        if self.retry_count <= self.max_retries:
            wait_time = self.backoff_factor * (2 ** (self.retry_count - 1))
            print(f"Retry {self.retry_count}/{self.max_retries} after {wait_time}s...")
            time.sleep(wait_time)
        else:
            print(f"Max retries ({self.max_retries}) reached. Giving up.")
            self.retry_count = 0