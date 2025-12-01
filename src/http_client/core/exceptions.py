"""
Иерархия исключений HTTP Client.

Классификация:
- TemporaryError (retryable=True) - можно ретраить
- FatalError (fatal=True) - НЕ ретраить никогда
"""

from typing import Optional
import requests

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BASE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class HTTPClientException(Exception):
    """Базовое исключение HTTP Client."""

    retryable: bool = False
    fatal: bool = False

    def __init__(self, message: str, **kwargs):
        self.message = message
        super().__init__(message)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ВРЕМЕННЫЕ ОШИБКИ (retryable=True)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TemporaryError(HTTPClientException):
    """
    Временная ошибка - можно ретраить.

    Примеры: таймауты, сетевые ошибки, 5xx серверов.
    """
    retryable = True

class NetworkError(TemporaryError):
    """Сетевая ошибка."""

    def __init__(self, message: str, url: Optional[str] = None):
        self.url = url
        full_message = f"{message}"
        if url:
            full_message += f" (url: {url})"
        super().__init__(full_message)

class TimeoutError(NetworkError):
    """
    Таймаут запроса.

    Args:
        message: Сообщение об ошибке
        url: URL запроса
        timeout: Значение таймаута
        timeout_type: Тип таймаута ('connect' или 'read')
    """

    def __init__(
        self,
        message: str,
        url: str,
        timeout: Optional[int] = None,
        timeout_type: Optional[str] = None
    ):
        self.timeout = timeout
        self.timeout_type = timeout_type

        msg = message
        if timeout_type:
            msg += f" ({timeout_type} timeout"
            if timeout:
                msg += f": {timeout}s"
            msg += ")"

        super().__init__(msg, url)

class ConnectionError(NetworkError):
    """
    Ошибка подключения.

    Примеры:
    - Connection refused
    - Connection reset
    - Network unreachable
    """
    pass

class ProxyError(NetworkError):
    """
    Ошибка прокси.

    Args:
        message: Сообщение
        url: URL
        proxy: Адрес прокси
    """

    def __init__(self, message: str, url: str, proxy: Optional[str] = None):
        self.proxy = proxy
        msg = message
        if proxy:
            msg += f" (proxy: {proxy})"
        super().__init__(msg, url)

class DNSError(NetworkError):
    """DNS resolution failed."""
    pass

class ServerError(TemporaryError):
    """
    5xx ошибка сервера.

    Args:
        status_code: HTTP статус код
        url: URL
        message: Дополнительное сообщение
    """

    def __init__(self, status_code: int, url: str, message: str = ""):
        self.status_code = status_code
        self.url = url

        msg = f"HTTP {status_code} error for {url}"
        if message:
            msg += f": {message}"

        super().__init__(msg)

class TooManyRequestsError(TemporaryError):
    """
    429 Rate Limit.

    Args:
        url: URL
        retry_after: Retry-After header value (seconds or datetime)
        message: Дополнительное сообщение
    """

    def __init__(
        self,
        url: str,
        retry_after: Optional[int] = None,
        message: str = ""
    ):
        self.url = url
        self.retry_after = retry_after

        msg = f"Rate limit exceeded for {url}"
        if retry_after:
            msg += f" (retry after {retry_after}s)"
        if message:
            msg += f": {message}"

        super().__init__(msg)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ФАТАЛЬНЫЕ ОШИБКИ (fatal=True)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class FatalError(HTTPClientException):
    """
    Фатальная ошибка - НЕ ретраить.

    Примеры: 4xx ошибки клиента, невалидный ответ.
    """
    fatal = True

class HTTPError(FatalError):
    """
    Базовая HTTP ошибка.

    Args:
        status_code: HTTP статус
        url: URL
        message: Сообщение
    """

    def __init__(self, status_code: int, url: str, message: str = ""):
        self.status_code = status_code
        self.url = url

        msg = f"HTTP {status_code} error for {url}"
        if message:
            msg += f": {message}"

        super().__init__(msg)

class BadRequestError(HTTPError):
    """400 Bad Request."""

    def __init__(self, url: str, message: str = ""):
        super().__init__(400, url, message)

class UnauthorizedError(HTTPError):
    """401 Unauthorized."""

    def __init__(self, url: str, message: str = ""):
        super().__init__(401, url, message)

class ForbiddenError(HTTPError):
    """403 Forbidden."""

    def __init__(self, url: str, message: str = ""):
        super().__init__(403, url, message)

class NotFoundError(HTTPError):
    """404 Not Found."""

    def __init__(self, url: str, message: str = ""):
        super().__init__(404, url, message)

class InvalidResponseError(FatalError):
    """
    Невалидный ответ.

    Примеры:
    - Битый JSON
    - Невалидная кодировка
    - Неожиданный формат данных
    """
    pass

class ResponseTooLargeError(FatalError):
    """
    Ответ слишком большой.

    Args:
        size: Размер ответа (bytes)
        max_size: Максимально допустимый размер
        url: URL
    """

    def __init__(self, size: int, max_size: int, url: str):
        self.size = size
        self.max_size = max_size
        self.url = url

        msg = (
            f"Response too large: {size} bytes "
            f"(max: {max_size}) for {url}"
        )
        super().__init__(msg)

class DecompressionBombError(FatalError):
    """
    Decompression bomb detected.

    Args:
        compressed_size: Размер сжатых данных
        decompressed_size: Размер распакованных данных
        url: URL
    """

    def __init__(
        self,
        compressed_size: int,
        decompressed_size: int,
        url: str
    ):
        self.compressed_size = compressed_size
        self.decompressed_size = decompressed_size
        self.url = url

        ratio = decompressed_size / compressed_size if compressed_size > 0 else 0

        msg = (
            f"Decompression bomb detected for {url}: "
            f"{compressed_size} -> {decompressed_size} bytes "
            f"(ratio: {ratio:.1f}x)"
        )
        super().__init__(msg)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# СПЕЦИАЛЬНЫЕ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TooManyRetriesError(HTTPClientException):
    """
    Исчерпаны все retry попытки.

    Args:
        max_retries: Количество попыток
        last_error: Последняя ошибка
        url: URL
    """

    def __init__(
        self,
        max_retries: int,
        last_error: Optional[Exception] = None,
        url: Optional[str] = None
    ):
        self.max_retries = max_retries
        self.last_error = last_error
        self.url = url

        msg = f"Max retries ({max_retries}) exceeded"
        if url:
            msg += f" for {url}"
        if last_error:
            msg += f". Last error: {str(last_error)}"

        super().__init__(msg)

class ConfigurationError(HTTPClientException):
    """Ошибка конфигурации."""
    fatal = True

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# УТИЛИТЫ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def classify_requests_exception(
    exc: Exception,
    url: str
) -> HTTPClientException:
    """
    Конвертировать requests.exceptions в наши исключения.

    Args:
        exc: Исключение из requests
        url: URL запроса

    Returns:
        Наше исключение с правильной классификацией

    Examples:
        >>> exc = requests.exceptions.Timeout()
        >>> our_exc = classify_requests_exception(exc, "https://example.com")
        >>> assert isinstance(our_exc, TimeoutError)
        >>> assert our_exc.retryable == True
    """

    if isinstance(exc, requests.exceptions.Timeout):
        return TimeoutError("Request timeout", url)

    elif isinstance(exc, requests.exceptions.ProxyError):
        return ProxyError("Proxy error", url)

    elif isinstance(exc, requests.exceptions.ConnectionError):
        return ConnectionError("Connection error", url)

    elif isinstance(exc, requests.exceptions.HTTPError):
        response = exc.response
        status_code = response.status_code if response is not None else 0

        if 400 <= status_code < 500:
            # 4xx - фатальные
            if status_code == 400:
                return BadRequestError(url)
            elif status_code == 401:
                return UnauthorizedError(url)
            elif status_code == 403:
                return ForbiddenError(url)
            elif status_code == 404:
                return NotFoundError(url)
            elif status_code == 429:
                retry_after = response.headers.get('Retry-After')
                return TooManyRequestsError(url, retry_after=retry_after)
            else:
                return HTTPError(status_code, url)

        elif 500 <= status_code < 600:
            # 5xx - временные
            return ServerError(status_code, url)

        else:
            return HTTPError(status_code, url)

    else:
        # Неизвестная ошибка - оборачиваем
        return HTTPClientException(str(exc))
