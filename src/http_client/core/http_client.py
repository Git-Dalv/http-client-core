# src/http_client/core/http_client.py
from typing import Any, Dict, List, Optional
import time

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException

from ..plugins.plugin import Plugin
from .config import HTTPClientConfig, TimeoutConfig
from .retry_engine import RetryEngine
from .error_handler import ErrorHandler
from .exceptions import (
    classify_requests_exception,
    TooManyRetriesError,
)


class HTTPClient:
    """
    Основной HTTP клиент с поддержкой плагинов и расширенной функциональностью.

    Features:
        - Connection pooling для переиспользования TCP соединений
        - Управление куками
        - Поддержка прокси
        - Контекстный менеджер для автоматического освобождения ресурсов
        - Immutable конфигурация для потокобезопасности
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
            base_url: Base URL (deprecated, use config)
            config: HTTPClientConfig instance
            plugins: List of plugins
            **kwargs: Config parameters (если config=None)
        """
        # Создать конфиг
        if config is None:
            config = HTTPClientConfig.create(base_url=base_url, **kwargs)

        # Immutable fields
        object.__setattr__(self, '_config', config)
        object.__setattr__(self, '_retry_engine', RetryEngine(config.retry))
        object.__setattr__(self, '_error_handler', ErrorHandler())
        object.__setattr__(self, '_plugins', list(plugins) if plugins else [])
        object.__setattr__(self, '_session', self._create_session())

        # Backward compatibility attributes
        object.__setattr__(self, '_timeout', config.timeout.read)  # Legacy: single timeout value
        object.__setattr__(self, '_proxies', config.proxies if config.proxies else None)
        object.__setattr__(self, '_verify_ssl', config.security.verify_ssl)

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
        Закрывает сессию и освобождает ресурсы.
        Рекомендуется вызывать после завершения работы с клиентом.
        """
        if hasattr(self, "_session"):
            self._session.close()

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
        Получает все текущие куки.

        Returns:
            Словарь с куками
        """
        return dict(self._session.cookies)

    # src/http_client/core/http_client.py

    # Замените метод set_cookie на этот:
    def set_cookie(self, name: str, value: str, domain: str = "", path: str = "/"):
        """
        Устанавливает куку.

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

        self._session.cookies.set(name, value, domain=domain, path=path)

    def remove_cookie(self, name: str, domain: str = None, path: str = "/"):
        """
        Удаляет конкретную куку.

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
        if domain is not None:
            # Удаляем из конкретного домена
            self._session.cookies.clear(domain=domain, path=path, name=name)
        else:
            # Удаляем из всех доменов
            cookies_to_remove = []
            for cookie in self._session.cookies:
                if cookie.name == name:
                    cookies_to_remove.append((cookie.domain, cookie.path))

            for cookie_domain, cookie_path in cookies_to_remove:
                self._session.cookies.clear(domain=cookie_domain, path=cookie_path, name=name)

    def clear_cookies(self):
        """Очищает все куки"""
        self._session.cookies.clear()

    # ==================== Управление заголовками ====================

    def set_header(self, key: str, value: str):
        """
        Устанавливает заголовок для всех последующих запросов.

        Args:
            key: Имя заголовка
            value: Значение заголовка
        """
        self._session.headers[key] = value

    def remove_header(self, key: str):
        """
        Удаляет заголовок.

        Args:
            key: Имя заголовка
        """
        if key in self._session.headers:
            del self._session.headers[key]

    def get_headers(self) -> Dict[str, str]:
        """
        Получает текущие заголовки.

        Returns:
            Словарь с заголовками
        """
        return dict(self._session.headers)

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
        Make HTTP request with retry logic.

        Args:
            method: HTTP method
            endpoint: URL endpoint
            **kwargs: Request parameters

        Returns:
            Response object
        """
        # Build full URL
        url = self._build_url(endpoint)

        # Timeout
        timeout = kwargs.pop('timeout', self._config.timeout.as_tuple())

        # Retry loop
        last_error = None

        while True:
            try:
                # Before request hooks
                for plugin in self._plugins:
                    try:
                        plugin.before_request(method=method, url=url, **kwargs)
                    except Exception as e:
                        print(f"Plugin {plugin.__class__.__name__} error in before_request: {e}")

                # Make request
                response = self._session.request(
                    method=method,
                    url=url,
                    timeout=timeout,
                    verify=self._config.security.verify_ssl,
                    allow_redirects=self._config.security.allow_redirects,
                    **kwargs
                )

                # Check status
                response.raise_for_status()

                # After response hooks
                for plugin in self._plugins:
                    try:
                        plugin.after_response(response=response)
                    except Exception as e:
                        print(f"Plugin {plugin.__class__.__name__} error in after_response: {e}")

                # Success - reset retry counter
                self._retry_engine.reset()

                return response

            except requests.exceptions.RequestException as e:
                # Classify error
                our_error = classify_requests_exception(e, url)
                last_error = our_error

                # Get response if exists
                response = getattr(e, 'response', None)

                # Error hooks
                for plugin in self._plugins:
                    try:
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
                    if self._retry_engine.attempt + 1 >= self._config.retry.max_attempts:
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

                # Log retry
                attempt = self._retry_engine.attempt + 1
                max_attempts = self._config.retry.max_attempts - 1  # Show as retries, not attempts
                print(f"Retry {attempt}/{max_attempts} after {wait_time:.1f}s...")

                # Wait
                time.sleep(wait_time)

                # Increment
                self._retry_engine.increment()

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

    # ==================== Свойства ====================

    @property
    def session(self) -> requests.Session:
        """
        Предоставляет прямой доступ к внутренней сессии.
        Используйте с осторожностью!

        Returns:
            Объект Session
        """
        return self._session

    @property
    def base_url(self) -> Optional[str]:
        """Base URL (read-only)."""
        return self._config.base_url

    @property
    def timeout(self) -> int:
        """Timeout (read-only). Returns read timeout for backward compatibility."""
        return self._config.timeout.read
