# src/http_client/core/error_handler.py

from typing import Optional

import requests
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
)
from requests.exceptions import (
    RequestException,
    Timeout,
)

from .exceptions import (
    BadRequestError,
    ConnectionError,
    ForbiddenError,
    HTTPClientException,
    HTTPError,
    NotFoundError,
    ServerError,
    TimeoutError,
    UnauthorizedError,
)


class ErrorHandler:
    """Класс для обработки ошибок HTTP запросов"""

    @staticmethod
    def handle_request_exception(error: Exception, url: str, timeout: Optional[int] = None) -> None:
        """Обрабатывает исключения requests и преобразует их в кастомные"""

        if isinstance(error, Timeout):
            raise TimeoutError(str(error), url, timeout or 0)

        elif isinstance(error, RequestsConnectionError):
            raise ConnectionError(str(error), url)

        elif isinstance(error, requests.exceptions.HTTPError):
            response = error.response
            ErrorHandler.handle_http_error(response)

        elif isinstance(error, RequestException):
            raise HTTPClientException(f"Request failed: {str(error)}")

        else:
            raise HTTPClientException(f"Unexpected error: {str(error)}")

    @staticmethod
    def handle_http_error(response: requests.Response) -> None:
        """Обрабатывает HTTP ошибки по статус коду"""

        if response is None:
            raise HTTPClientException("HTTP error occurred but no response object available")

        status_code = response.status_code
        url = str(response.url)
        message = response.text[:200] if response.text else ""

        if status_code == 400:
            raise BadRequestError(url, message)

        elif status_code == 401:
            raise UnauthorizedError(url, message)

        elif status_code == 403:
            raise ForbiddenError(url, message)

        elif status_code == 404:
            raise NotFoundError(url, message)

        elif 500 <= status_code < 600:
            raise ServerError(status_code, url, message)

        else:
            raise HTTPError(status_code, url, message)

    @staticmethod
    def is_retryable_error(error: Exception) -> bool:
        """Проверяет, можно ли повторить запрос после этой ошибки"""

        # Повторяем при ошибках подключения, таймаутах и серверных ошибках
        retryable_errors = (ConnectionError, TimeoutError, ServerError)

        return isinstance(error, retryable_errors)
