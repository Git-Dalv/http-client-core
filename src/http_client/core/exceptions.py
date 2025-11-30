# src/http_client/core/exceptions.py


class HTTPClientException(Exception):
    """Базовое исключение для HTTP клиента"""

    pass


class ConnectionError(HTTPClientException):
    """Ошибка подключения"""

    def __init__(self, message: str, url: str):
        self.url = url
        super().__init__(f"Connection error to {url}: {message}")


class TimeoutError(HTTPClientException):
    """Ошибка таймаута"""

    def __init__(self, message: str, url: str, timeout: int):
        self.url = url
        self.timeout = timeout
        super().__init__(f"Timeout error ({timeout}s) for {url}: {message}")


class HTTPError(HTTPClientException):
    """Ошибка HTTP ответа"""

    def __init__(self, status_code: int, url: str, message: str = ""):
        self.status_code = status_code
        self.url = url
        super().__init__(f"HTTP {status_code} error for {url}: {message}")


class BadRequestError(HTTPError):
    """Ошибка 400 - Bad Request"""

    def __init__(self, url: str, message: str = ""):
        super().__init__(400, url, message)


class UnauthorizedError(HTTPError):
    """Ошибка 401 - Unauthorized"""

    def __init__(self, url: str, message: str = ""):
        super().__init__(401, url, message)


class ForbiddenError(HTTPError):
    """Ошибка 403 - Forbidden"""

    def __init__(self, url: str, message: str = ""):
        super().__init__(403, url, message)


class NotFoundError(HTTPError):
    """Ошибка 404 - Not Found"""

    def __init__(self, url: str, message: str = ""):
        super().__init__(404, url, message)


class ServerError(HTTPError):
    """Ошибка 5xx - Server Error"""

    def __init__(self, status_code: int, url: str, message: str = ""):
        super().__init__(status_code, url, message)


class ValidationError(HTTPClientException):
    """Ошибка валидации данных"""

    def __init__(self, message: str, field: str = None):
        self.field = field
        error_msg = "Validation error"
        if field:
            error_msg += f" for field '{field}'"
        error_msg += f": {message}"
        super().__init__(error_msg)
