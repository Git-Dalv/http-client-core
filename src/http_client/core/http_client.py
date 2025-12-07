# src/http_client/core/http_client.py
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import time
import warnings
import threading
import weakref
import atexit

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException

from ..plugins.plugin import Plugin
from .config import HTTPClientConfig, TimeoutConfig
from .retry_engine import RetryEngine
from .error_handler import ErrorHandler
from .session_manager import ThreadSafeSessionManager
from .context import RequestContext
from .exceptions import (
    classify_requests_exception,
    TooManyRetriesError,
    ResponseTooLargeError,
    DecompressionBombError,
)

# Delayed import to avoid circular dependency
if TYPE_CHECKING:
    from .logging import HTTPClientLogger


# Module-level thread-local storage for request context
_request_context = threading.local()


def get_current_request_context() -> Optional[Dict[str, Any]]:
    """
    Get current request context (thread-safe).

    Returns None if called outside of request context.
    Used by plugins to access request parameters in after_response hook.

    Returns:
        Dictionary with 'method', 'url', and 'kwargs' keys, or None

    Example:
        >>> # In plugin's after_response hook:
        >>> context = get_current_request_context()
        >>> if context:
        ...     method = context['method']
        ...     url = context['url']
        ...     params = context['kwargs'].get('params', {})
    """
    return getattr(_request_context, 'data', None)


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Рекурсивное слияние словарей (deep merge).

    Используется для корректного объединения kwargs из нескольких плагинов,
    чтобы не терять вложенные значения (например, headers).

    Args:
        base: Базовый словарь
        override: Словарь с переопределениями

    Returns:
        Новый словарь с объединенными значениями

    Example:
        >>> base = {"headers": {"Authorization": "Bearer token"}, "timeout": 30}
        >>> override = {"headers": {"X-Custom": "value"}, "params": {"page": 1}}
        >>> result = _deep_merge(base, override)
        >>> # result = {
        ...     "headers": {"Authorization": "Bearer token", "X-Custom": "value"},
        ...     "timeout": 30,
        ...     "params": {"page": 1}
        ... }
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Рекурсивное слияние для вложенных словарей
            result[key] = _deep_merge(result[key], value)
        else:
            # Простое переопределение для остальных типов
            result[key] = value
    return result


class HTTPClient:
    """
    Основной HTTP клиент с поддержкой плагинов и расширенной функциональностью.

    Features:
        - Connection pooling для переиспользования TCP соединений
        - Управление куками
        - Поддержка прокси
        - Контекстный менеджер для автоматического освобождения ресурсов
        - Immutable конфигурация для потокобезопасности
        - Thread-safe: каждый поток получает собственную сессию
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        config: Optional[HTTPClientConfig] = None,
        plugins: Optional[List[Plugin]] = None,
        **kwargs
    ):
        """
        Initialize HTTP client.

        Args:
            base_url: Base URL (deprecated, use config.base_url)
            config: HTTPClientConfig instance
            plugins: List of plugins
            **kwargs: Config parameters (deprecated, use config object)

        Deprecated Parameters:
            max_retries: Use config.retry.max_attempts instead
            verify_ssl: Use config.security.verify_ssl instead
            pool_connections: Use config.pool.pool_connections instead
            pool_maxsize: Use config.pool.pool_maxsize instead
            max_redirects: Use config.pool.max_redirects instead
        """
        # Check for deprecated parameters
        deprecated_params = {
            'max_retries': 'config.retry.max_attempts',
            'verify_ssl': 'config.security.verify_ssl',
            'max_redirects': 'config.pool.max_redirects',
            'pool_connections': 'config.pool.pool_connections',
            'pool_maxsize': 'config.pool.pool_maxsize',
            'pool_block': 'config.pool.pool_block',
        }

        for param, replacement in deprecated_params.items():
            if param in kwargs:
                warnings.warn(
                    f"Parameter '{param}' is deprecated. Use '{replacement}' instead. "
                    f"This parameter will be removed in version 2.0.0",
                    DeprecationWarning,
                    stacklevel=2
                )

        # Создать конфиг
        if config is None:
            config = HTTPClientConfig.create(base_url=base_url, **kwargs)

        # Immutable fields
        object.__setattr__(self, '_config', config)
        object.__setattr__(self, '_retry_engine', RetryEngine(config.retry))
        object.__setattr__(self, '_error_handler', ErrorHandler())
        object.__setattr__(self, '_plugins', list(plugins) if plugins else [])

        # Initialize logger if logging config provided
        logger_instance: Optional['HTTPClientLogger'] = None
        if config.logging:
            from .logging import HTTPClientLogger
            # Use base_url in logger name for uniqueness
            logger_name = "http_client"
            if config.base_url:
                # Extract domain from base_url
                from urllib.parse import urlparse
                parsed = urlparse(config.base_url)
                domain = parsed.netloc if parsed.netloc else (parsed.path.split('/')[0] if parsed.path else "unknown")
                logger_name = f"http_client.{domain}"

            logger_instance = HTTPClientLogger(
                config=config.logging,
                name=logger_name
            )

        object.__setattr__(self, '_logger', logger_instance)

        # Thread-safe session manager - each thread gets its own session
        object.__setattr__(
            self,
            '_session_manager',
            ThreadSafeSessionManager(session_factory=self._create_session)
        )

        # Backward compatibility attributes
        object.__setattr__(self, '_timeout', config.timeout.read)  # Legacy: single timeout value
        object.__setattr__(self, '_proxies', config.proxies if config.proxies else None)
        object.__setattr__(self, '_verify_ssl', config.security.verify_ssl)

        # Graceful shutdown: weak reference for __del__ and atexit cleanup
        object.__setattr__(self, '_weak_self', weakref.ref(self))
        atexit.register(self._atexit_cleanup)

        object.__setattr__(self, '_initialized', True)

    def __setattr__(self, name, value):
        """Запретить изменение после init (immutability)."""
        if hasattr(self, '_initialized'):
            raise RuntimeError(
                f"Cannot modify '{name}' - HTTPClient is immutable. "
                f"Create new instance instead."
            )
        object.__setattr__(self, name, value)

    def __enter__(self):
        """Поддержка контекстного менеджера"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие сессии при выходе из контекста"""
        self.close()
        return False

    def _create_session(self) -> requests.Session:
        """Create configured session."""
        session = requests.Session()

        # Connection pool adapter
        adapter = HTTPAdapter(
            pool_connections=self._config.pool.pool_connections,
            pool_maxsize=self._config.pool.pool_maxsize,
            pool_block=self._config.pool.pool_block,
            max_retries=0  # Ретраи через RetryEngine
        )

        session.mount('http://', adapter)
        session.mount('https://', adapter)

        # Headers
        if self._config.headers:
            session.headers.update(self._config.headers)

        # Proxies
        if self._config.proxies:
            session.proxies.update(self._config.proxies)

        return session

    # ==================== Управление жизненным циклом ====================

    def close(self):
        """
        Закрывает все сессии (из всех потоков) и освобождает ресурсы.
        Рекомендуется вызывать после завершения работы с клиентом.

        Thread-safe: закрывает сессии из всех потоков, которые использовали клиент.

        Cleanup order:
            1. Logger handlers (flush and close file descriptors)
            2. Session connections (close all thread-local sessions)
        """
        # Close logger first (flush and close file handlers)
        if hasattr(self, "_logger") and self._logger is not None:
            try:
                self._logger.close()
            except Exception:
                # Ignore errors during cleanup
                pass

        # Then close sessions
        if hasattr(self, "_session_manager"):
            self._session_manager.close_all()

    def __del__(self):
        """
        Деструктор с предупреждением о незакрытых ресурсах.

        Автоматически вызывает close() при garbage collection,
        но выдает ResourceWarning если сессии не были закрыты явно.

        Best practice: использовать context manager или явно вызывать close()
        """
        try:
            # Check if session manager exists and has active sessions
            if hasattr(self, "_session_manager"):
                count = self._session_manager.get_active_sessions_count()
                if count > 0:
                    warnings.warn(
                        f"HTTPClient garbage collected with {count} unclosed session(s). "
                        "Use 'with HTTPClient() as client:' or call client.close() explicitly. "
                        "Unclosed sessions may leak resources and file descriptors.",
                        ResourceWarning,
                        stacklevel=2
                    )
                    # Auto-close to prevent resource leaks
                    self.close()
        except Exception:
            # Ignore errors during garbage collection
            # (may occur if Python is shutting down)
            pass

    def _atexit_cleanup(self):
        """Graceful shutdown при завершении программы."""
        try:
            client = self._weak_self()
            if client is not None:
                client.close()
        except Exception:
            # Ignore errors during program termination
            pass

    def health_check(self, test_url: Optional[str] = None, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Проверяет состояние клиента и возвращает диагностическую информацию.

        Полезно для:
        - Health endpoints в веб-приложениях
        - Мониторинга состояния клиента
        - Диагностики проблем с соединением

        Args:
            test_url: URL для проверки соединения (опционально).
                      Если указан, выполняется HEAD запрос.
            timeout: Таймаут для тестового запроса (секунды)

        Returns:
            Словарь с диагностической информацией:
            {
                "healthy": bool,           # Общий статус здоровья
                "base_url": str | None,    # Базовый URL клиента
                "active_sessions": int,    # Количество активных сессий
                "plugins_count": int,      # Количество подключенных плагинов
                "plugins": list[str],      # Имена плагинов
                "config": {                # Краткая информация о конфиге
                    "timeout_connect": float,
                    "timeout_read": float,
                    "max_retries": int,
                    "verify_ssl": bool,
                },
                "connectivity": {          # Только если test_url указан
                    "url": str,
                    "reachable": bool,
                    "response_time_ms": float | None,
                    "status_code": int | None,
                    "error": str | None,
                } | None,
            }

        Example:
            >>> client = HTTPClient(base_url="https://api.example.com")
            >>> health = client.health_check()
            >>> print(health["healthy"])
            True

            >>> # С проверкой соединения
            >>> health = client.health_check(test_url="https://api.example.com/health")
            >>> print(health["connectivity"]["reachable"])
            True
        """
        result = {
            "healthy": True,
            "base_url": self.base_url,
            "active_sessions": 0,
            "plugins_count": len(self._plugins),
            "plugins": [p.__class__.__name__ for p in self._plugins],
            "config": {
                "timeout_connect": self._config.timeout.connect,
                "timeout_read": self._config.timeout.read,
                "max_retries": self._config.retry.max_attempts,
                "verify_ssl": self._config.security.verify_ssl,
            },
            "connectivity": None,
        }

        # Получаем количество активных сессий
        try:
            result["active_sessions"] = self._session_manager.get_active_sessions_count()
        except Exception:
            result["active_sessions"] = -1  # Ошибка получения

        # Проверка соединения если указан test_url
        if test_url:
            connectivity = {
                "url": test_url,
                "reachable": False,
                "response_time_ms": None,
                "status_code": None,
                "error": None,
            }

            try:
                start_time = time.time()

                # Используем HEAD для минимальной нагрузки
                response = self.session.head(
                    test_url,
                    timeout=timeout,
                    verify=self._config.security.verify_ssl,
                    allow_redirects=True,
                )

                response_time = (time.time() - start_time) * 1000  # ms

                connectivity["reachable"] = True
                connectivity["response_time_ms"] = round(response_time, 2)
                connectivity["status_code"] = response.status_code

            except requests.exceptions.Timeout:
                connectivity["error"] = "Connection timeout"
                result["healthy"] = False
            except requests.exceptions.ConnectionError as e:
                connectivity["error"] = f"Connection error: {str(e)[:100]}"
                result["healthy"] = False
            except requests.exceptions.RequestException as e:
                connectivity["error"] = f"Request error: {str(e)[:100]}"
                result["healthy"] = False
            except Exception as e:
                connectivity["error"] = f"Unexpected error: {str(e)[:100]}"
                result["healthy"] = False

            result["connectivity"] = connectivity

        return result

    # ==================== Управление плагинами ====================

    def add_plugin(self, plugin: Plugin):
        """
        Добавляет плагин к клиенту.

        Args:
            plugin: Экземпляр плагина
        """
        self._plugins.append(plugin)

    def remove_plugin(self, plugin: Plugin):
        """
        Удаляет плагин из клиента.

        Args:
            plugin: Экземпляр плагина для удаления
        """
        if plugin in self._plugins:
            self._plugins.remove(plugin)

    def clear_plugins(self):
        """Удаляет все плагины"""
        self._plugins.clear()

    # ==================== Управление куками ====================

    def get_cookies(self) -> Dict[str, str]:
        """
        Получает все текущие куки для текущего потока.

        Returns:
            Словарь с куками
        """
        return dict(self.session.cookies)

    # src/http_client/core/http_client.py

    # Замените метод set_cookie на этот:
    def set_cookie(self, name: str, value: str, domain: str = "", path: str = "/"):
        """
        Устанавливает куку для текущего потока.

        Args:
            name: Имя куки
            value: Значение куки
            domain: Домен для куки (пустая строка = supercookie для всех доменов)
            path: Путь для куки

        Example:
            # Кука для всех доменов
            client.set_cookie("session_id", "abc123")

            # Кука для конкретного домена
            client.set_cookie("user_token", "xyz", domain="example.com")
        """
        # Если domain не указан или None, используем пустую строку (supercookie)
        if domain is None:
            domain = ""

        self.session.cookies.set(name, value, domain=domain, path=path)

    def remove_cookie(self, name: str, domain: str = None, path: str = "/"):
        """
        Удаляет конкретную куку для текущего потока.

        Args:
            name: Имя куки
            domain: Домен куки (None = удалить из всех доменов)
            path: Путь куки

        Example:
            # Удалить куку из всех доменов
            client.remove_cookie("session_id")

            # Удалить куку из конкретного домена
            client.remove_cookie("user_token", domain="example.com")
        """
        session = self.session
        if domain is not None:
            # Удаляем из конкретного домена
            session.cookies.clear(domain=domain, path=path, name=name)
        else:
            # Удаляем из всех доменов
            cookies_to_remove = []
            for cookie in session.cookies:
                if cookie.name == name:
                    cookies_to_remove.append((cookie.domain, cookie.path))

            for cookie_domain, cookie_path in cookies_to_remove:
                session.cookies.clear(domain=cookie_domain, path=cookie_path, name=name)

    def clear_cookies(self):
        """Очищает все куки для текущего потока"""
        self.session.cookies.clear()

    # ==================== Управление заголовками ====================

    def set_header(self, key: str, value: str):
        """
        Устанавливает заголовок для всех последующих запросов в текущем потоке.

        Args:
            key: Имя заголовка
            value: Значение заголовка
        """
        self.session.headers[key] = value

    def remove_header(self, key: str):
        """
        Удаляет заголовок для текущего потока.

        Args:
            key: Имя заголовка
        """
        session = self.session
        if key in session.headers:
            del session.headers[key]

    def get_headers(self) -> Dict[str, str]:
        """
        Получает текущие заголовки для текущего потока.

        Returns:
            Словарь с заголовками
        """
        return dict(self.session.headers)

    # ==================== Управление прокси ====================

    def set_proxies(self, proxies: Dict[str, str]):
        """
        Устанавливает прокси для последующих запросов.

        Args:
            proxies: Словарь с прокси {'http': 'http://proxy:port', 'https': 'https://proxy:port'}
        """
        # Создаем новый атрибут через object.__setattr__ чтобы обойти immutability
        object.__setattr__(self, "_proxies", proxies)

    def get_proxies(self) -> Optional[Dict[str, str]]:
        """
        Получает текущие прокси.

        Returns:
            Словарь с прокси или None
        """
        return self._proxies

    def clear_proxies(self):
        """Удаляет прокси"""
        object.__setattr__(self, "_proxies", None)

    # ==================== Внутренние методы ====================

    def _execute_before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Выполняет before_request для всех плагинов.

        Args:
            method: HTTP метод
            url: URL запроса
            **kwargs: Дополнительные параметры запроса

        Returns:
            Обновленные параметры запроса
        """
        for plugin in self._plugins:
            kwargs = plugin.before_request(method, url, **kwargs)
        return kwargs

    def _execute_after_response(self, response: requests.Response) -> requests.Response:
        """
        Выполняет after_response для всех плагинов.

        Args:
            response: Объект ответа

        Returns:
            Обработанный ответ
        """
        for plugin in self._plugins:
            response = plugin.after_response(response)
        return response

    def _execute_on_error(self, exception: Exception, **kwargs: Any) -> bool:
        """
        Выполняет on_error хуки всех плагинов.

        Args:
            exception: Исключение которое произошло
            **kwargs: Дополнительные параметры

        Returns:
            True если хотя бы один плагин хочет повторить запрос (retry)
            False если исключение должно быть выброшено
        """
        should_retry = False
        for plugin in self._plugins:
            try:
                # ВАЖНО: передаем method и url в kwargs
                result = plugin.on_error(exception, **kwargs)
                # Если хотя бы один плагин вернул True - делаем retry
                if result is True:
                    should_retry = True
            except Exception as plugin_error:
                # Логируем ошибку плагина, но не прерываем выполнение
                print(f"Plugin {plugin.__class__.__name__} error in on_error: {plugin_error}")

        return should_retry

    def _build_url(self, endpoint: str) -> str:
        """
        Строит полный URL из base_url и endpoint.

        Args:
            endpoint: Endpoint запроса

        Returns:
            Полный URL
        """
        # Если endpoint - абсолютный URL, используем его как есть
        if endpoint.startswith(("http://", "https://")):
            return endpoint

        # Убираем начальный слеш из endpoint если есть
        endpoint = endpoint.lstrip("/")

        # Склеиваем base_url и endpoint
        base = self._config.base_url
        if base:
            base = base.rstrip("/")
            return f"{base}/{endpoint}"
        return endpoint

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request with retry logic and logging.

        Args:
            method: HTTP method
            endpoint: URL endpoint
            **kwargs: Request parameters

        Returns:
            Response object
        """
        # Build full URL
        url = self._build_url(endpoint)

        # Add correlation ID for request tracing
        import uuid

        # Get or create correlation ID
        if 'headers' not in kwargs:
            kwargs['headers'] = {}

        correlation_id = kwargs['headers'].get('X-Correlation-ID')
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
            kwargs['headers']['X-Correlation-ID'] = correlation_id

        # Create request context for v2 plugins
        ctx = RequestContext(
            method=method,
            url=url,
            kwargs=kwargs.copy(),
            request_id=correlation_id  # Use same ID as correlation ID
        )

        # Store request context for v1 plugins (thread-safe, backward compatibility)
        _request_context.data = {
            'method': method,
            'url': url,
            'kwargs': kwargs.copy()
        }

        # Set correlation ID in logging context
        if self._logger:
            from .logging.filters import set_correlation_id
            set_correlation_id(correlation_id)
            self._logger.debug(
                "Request initialized",
                method=method,
                url=url,
                correlation_id=correlation_id,
                has_json="json" in kwargs,
                has_data="data" in kwargs
            )

        # Start timing
        start_time = time.time()

        # Timeout
        timeout = kwargs.pop('timeout', self._config.timeout.as_tuple())

        # Log request started
        if self._logger:
            self._logger.info(
                "Request started",
                method=method,
                url=url,
                correlation_id=correlation_id,
                timeout=self._config.timeout.total or self._config.timeout.read,
                max_retries=self._config.retry.max_attempts - 1
            )

        # Retry loop
        last_error = None

        try:
            while True:
                try:
                    # Before request hooks (support both v1 and v2 APIs)
                    for plugin in self._plugins:
                        try:
                            # Lazy import to avoid circular dependency
                            from ..plugins.base_v2 import PluginV2

                            if isinstance(plugin, PluginV2):
                                # V2 API - receives RequestContext, can return Response
                                result = plugin.before_request(ctx)
                                if result is not None:
                                    # Short-circuit with response from plugin
                                    return result
                                # Apply modified kwargs from context (deep merge for nested dicts like headers)
                                kwargs = _deep_merge(kwargs, ctx.kwargs)
                            else:
                                # V1 API - legacy support
                                result = plugin.before_request(method=method, url=url, **kwargs)

                                # Check if plugin returned cached response (short-circuit)
                                if isinstance(result, dict):
                                    if '__cached_response__' in result:
                                        # Return cached response immediately, skip HTTP call
                                        return result['__cached_response__']
                                    # Update kwargs with plugin modifications (deep merge for nested dicts like headers)
                                    kwargs = _deep_merge(kwargs, result)
                        except Exception as e:
                            print(f"Plugin {plugin.__class__.__name__} error in before_request: {e}")

                    # Filter out internal parameters (starting with '_') before passing to requests
                    # These are used by plugins for internal tracking and should not be passed to requests.Session
                    internal_params = {k: v for k, v in kwargs.items() if k.startswith('_')}
                    clean_kwargs = {k: v for k, v in kwargs.items() if not k.startswith('_')}

                    # Make request (using thread-local session)
                    response = self.session.request(
                        method=method,
                        url=url,
                        timeout=timeout,
                        verify=self._config.security.verify_ssl,
                        allow_redirects=self._config.security.allow_redirects,
                        **clean_kwargs
                    )

                    # Attach internal parameters to response.request for plugin access
                    if internal_params and hasattr(response, 'request'):
                        for key, value in internal_params.items():
                            setattr(response.request, key, value)

                    # Check status
                    response.raise_for_status()

                    # Validate response size
                    content_length = response.headers.get('Content-Length')
                    if content_length:
                        size = int(content_length)
                        if size > self._config.security.max_response_size:
                            raise ResponseTooLargeError(
                                f"Response size ({size} bytes) exceeds maximum "
                                f"({self._config.security.max_response_size} bytes)",
                                url=url,
                                size=size
                            )

                    # Check actual content size (if Content-Length not present)
                    if len(response.content) > self._config.security.max_response_size:
                        raise ResponseTooLargeError(
                            f"Response size ({len(response.content)} bytes) exceeds maximum "
                            f"({self._config.security.max_response_size} bytes)",
                            url=url,
                            size=len(response.content)
                        )

                    # Check for decompression bomb (after size check)
                    if 'gzip' in response.headers.get('Content-Encoding', '').lower():
                        compressed_size = len(response.content)
                        # Try to get uncompressed size from response
                        try:
                            import gzip
                            import io

                            # Peek at decompressed size
                            with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as gz:
                                # Read in chunks to avoid loading everything
                                uncompressed_size = 0
                                chunk_size = 8192
                                while True:
                                    chunk = gz.read(chunk_size)
                                    if not chunk:
                                        break
                                    uncompressed_size += len(chunk)

                                    # Check ratio on the fly (защита от decompression bomb)
                                    if compressed_size > 0:
                                        ratio = uncompressed_size / compressed_size
                                        if ratio > self._config.security.max_compression_ratio:
                                            raise DecompressionBombError(
                                                f"Potential decompression bomb detected: "
                                                f"ratio {ratio:.1f}:1 (compressed: {compressed_size}, "
                                                f"uncompressed: {uncompressed_size}+) "
                                                f"exceeds max allowed ratio {self._config.security.max_compression_ratio}:1",
                                                url=url
                                            )

                                    # Also check absolute size
                                    if uncompressed_size > self._config.security.max_decompressed_size:
                                        raise DecompressionBombError(
                                            f"Decompressed size ({uncompressed_size} bytes) exceeds maximum "
                                            f"({self._config.security.max_decompressed_size} bytes)",
                                            url=url
                                        )
                        except DecompressionBombError:
                            raise
                        except Exception:
                            # If we can't check, proceed cautiously
                            pass

                    # After response hooks (support both v1 and v2 APIs)
                    for plugin in self._plugins:
                        try:
                            # Lazy import to avoid circular dependency
                            from ..plugins.base_v2 import PluginV2

                            if isinstance(plugin, PluginV2):
                                # V2 API - receives RequestContext and Response
                                response = plugin.after_response(ctx, response)
                            else:
                                # V1 API - only receives Response
                                response = plugin.after_response(response=response)
                        except Exception as e:
                            print(f"Plugin {plugin.__class__.__name__} error in after_response: {e}")

                    # Success - Log completion
                    if self._logger:
                        duration_ms = round((time.time() - start_time) * 1000, 2)
                        attempt = self._retry_engine.attempt + 1
                        self._logger.info(
                            "Request completed",
                            method=method,
                            url=url,
                            status_code=response.status_code,
                            duration_ms=duration_ms,
                            attempt=attempt,
                            response_size=len(response.content),
                            correlation_id=correlation_id
                        )

                    # Reset retry counter
                    self._retry_engine.reset()

                    return response

                except requests.exceptions.RequestException as e:
                    # Classify error
                    our_error = classify_requests_exception(e, url)
                    last_error = our_error

                    # Get response if exists
                    response = getattr(e, 'response', None)

                    # Error hooks (support both v1 and v2 APIs)
                    for plugin in self._plugins:
                        try:
                            # Lazy import to avoid circular dependency
                            from ..plugins.base_v2 import PluginV2

                            if isinstance(plugin, PluginV2):
                                # V2 API - receives RequestContext and error
                                plugin.on_error(ctx, our_error)
                            else:
                                # V1 API - receives individual parameters
                                plugin.on_error(
                                    error=our_error,
                                    method=method,
                                    url=url,
                                    response=response
                                )
                        except Exception as plugin_error:
                            print(f"Plugin {plugin.__class__.__name__} error in on_error: {plugin_error}")

                    # Check if should retry
                    if not self._retry_engine.should_retry(method, our_error, response):
                        # Check if it's because we hit max attempts
                        is_max_attempts = self._retry_engine.attempt + 1 >= self._config.retry.max_attempts

                        # Log error
                        if self._logger:
                            duration_ms = round((time.time() - start_time) * 1000, 2)
                            self._logger.error(
                                "Request failed",
                                method=method,
                                url=url,
                                error=str(our_error),
                                error_type=type(our_error).__name__,
                                attempt=self._retry_engine.attempt + 1,
                                max_attempts=self._config.retry.max_attempts,
                                duration_ms=duration_ms,
                                correlation_id=correlation_id,
                                is_max_attempts=is_max_attempts
                            )

                        if is_max_attempts:
                            raise TooManyRetriesError(
                                max_retries=self._config.retry.max_attempts - 1,  # Convert attempts to retries
                                last_error=last_error,
                                url=url
                            )
                        else:
                            # It's a fatal error or non-idempotent method
                            raise our_error

                    # Get wait time
                    wait_time = self._retry_engine.get_wait_time(our_error, response)

                    # Log retry warning
                    attempt = self._retry_engine.attempt + 1
                    max_attempts = self._config.retry.max_attempts

                    if self._logger:
                        duration_ms = round((time.time() - start_time) * 1000, 2)
                        self._logger.warning(
                            "Request error (will retry)",
                            method=method,
                            url=url,
                            error=str(our_error),
                            error_type=type(our_error).__name__,
                            attempt=attempt,
                            max_attempts=max_attempts,
                            duration_ms=duration_ms,
                            wait_time_s=round(wait_time, 2),
                            correlation_id=correlation_id
                        )
                    else:
                        # Fallback to print if no logger
                        print(f"[{correlation_id}] Retry {attempt}/{max_attempts - 1} after {wait_time:.1f}s...")

                    # Wait
                    time.sleep(wait_time)

                    # Increment
                    self._retry_engine.increment()
        finally:
            # Clear correlation ID from context
            if self._logger:
                from .logging.filters import clear_correlation_id
                clear_correlation_id()

            # Clear request context (thread-safe cleanup)
            _request_context.data = None

    def get(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """
        Выполняет GET запрос.

        Args:
            endpoint: Endpoint или полный URL
            **kwargs: Дополнительные параметры (params, headers и т.д.)

        Returns:
            Объект Response
        """
        return self._request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """
        Выполняет POST запрос.

        Args:
            endpoint: Endpoint или полный URL
            **kwargs: Дополнительные параметры (json, data, headers и т.д.)

        Returns:
            Объект Response
        """
        return self._request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """
        Выполняет PUT запрос.

        Args:
            endpoint: Endpoint или полный URL
            **kwargs: Дополнительные параметры

        Returns:
            Объект Response
        """
        return self._request("PUT", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """
        Выполняет DELETE запрос.

        Args:
            endpoint: Endpoint или полный URL
            **kwargs: Дополнительные параметры

        Returns:
            Объект Response
        """
        return self._request("DELETE", endpoint, **kwargs)

    def patch(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """
        Выполняет PATCH запрос.

        Args:
            endpoint: Endpoint или полный URL
            **kwargs: Дополнительные параметры

        Returns:
            Объект Response
        """
        return self._request("PATCH", endpoint, **kwargs)

    def head(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """
        Выполняет HEAD запрос.

        Args:
            endpoint: Endpoint или полный URL
            **kwargs: Дополнительные параметры

        Returns:
            Объект Response
        """
        return self._request("HEAD", endpoint, **kwargs)

    def options(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """
        Выполняет OPTIONS запрос.

        Args:
            endpoint: Endpoint или полный URL
            **kwargs: Дополнительные параметры

        Returns:
            Объект Response
        """
        return self._request("OPTIONS", endpoint, **kwargs)

    def download(
        self,
        endpoint: str,
        file_path: str,
        chunk_size: int = 8192,
        show_progress: bool = False,
        **kwargs
    ) -> int:
        """
        Download large file with streaming to avoid memory issues.

        Args:
            endpoint: URL endpoint
            file_path: Path to save file
            chunk_size: Size of chunks to download (default 8KB)
            show_progress: Show download progress (requires tqdm)
            **kwargs: Additional request parameters

        Returns:
            Total bytes downloaded

        Example:
            >>> client = HTTPClient(base_url="https://example.com")
            >>> bytes_downloaded = client.download("/large-file.zip", "output.zip")
            >>> print(f"Downloaded {bytes_downloaded} bytes")
        """
        url = self._build_url(endpoint)

        # Force stream mode
        kwargs['stream'] = True

        # Timeout
        timeout = kwargs.pop('timeout', self._config.timeout.as_tuple())

        # Make request (using thread-local session)
        response = self.session.get(
            url,
            timeout=timeout,
            verify=self._config.security.verify_ssl,
            **kwargs
        )

        response.raise_for_status()

        # Get total size if available
        total_size = int(response.headers.get('Content-Length', 0))

        # Check if exceeds limit
        if total_size > self._config.security.max_response_size:
            raise ResponseTooLargeError(
                f"File size ({total_size} bytes) exceeds maximum "
                f"({self._config.security.max_response_size} bytes)",
                url=url,
                size=total_size
            )

        # Download with progress
        downloaded = 0

        try:
            if show_progress:
                try:
                    from tqdm import tqdm
                    progress_bar = tqdm(total=total_size, unit='B', unit_scale=True)
                except ImportError:
                    progress_bar = None
                    print("Install tqdm for progress bar: pip install tqdm")
            else:
                progress_bar = None

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:  # Filter out keep-alive chunks
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_bar:
                            progress_bar.update(len(chunk))

                        # Check size limit
                        if downloaded > self._config.security.max_response_size:
                            raise ResponseTooLargeError(
                                f"Downloaded size ({downloaded} bytes) exceeds maximum",
                                url=url,
                                size=downloaded
                            )

            if progress_bar:
                progress_bar.close()

            return downloaded

        except Exception as e:
            # Clean up partial file
            import os
            if os.path.exists(file_path):
                os.remove(file_path)
            raise

    # ==================== Свойства ====================

    @property
    def session(self) -> requests.Session:
        """
        Предоставляет прямой доступ к thread-local сессии.

        Каждый поток получает свою собственную изолированную сессию.
        Сессия создается лениво при первом обращении из потока.

        Thread-safe: безопасно использовать из нескольких потоков.

        Returns:
            Объект Session для текущего потока
        """
        return self._session_manager.get_session()

    @property
    def base_url(self) -> Optional[str]:
        """Base URL (read-only)."""
        return self._config.base_url

    @property
    def timeout(self) -> int:
        """Timeout (read-only). Returns read timeout for backward compatibility."""
        return self._config.timeout.read
