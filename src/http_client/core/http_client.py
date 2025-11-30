# src/http_client/core/http_client.py
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException

from ..plugins.plugin import Plugin
from .error_handler import ErrorHandler


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
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 10,
        proxies: Optional[Dict[str, str]] = None,
        pool_connections: int = 10,
        pool_maxsize: int = 10,
        max_redirects: int = 30,
        verify_ssl: bool = True,
    ):
        """
        Инициализация HTTP клиента.

        Args:
            base_url: Базовый URL для всех запросов
            headers: Заголовки по умолчанию
            timeout: Таймаут запроса в секундах
            proxies: Прокси серверы {'http': 'http://proxy:port', 'https': 'https://proxy:port'}
            pool_connections: Количество пулов соединений для кеширования
            pool_maxsize: Максимальное количество соединений в пуле
            max_redirects: Максимальное количество редиректов
            verify_ssl: Проверять SSL сертификаты
        """
        # Сохраняем конфигурацию
        self._base_url = base_url.rstrip("/")
        self._headers = headers if headers else {}
        self._timeout = timeout
        self._proxies = proxies
        self._verify_ssl = verify_ssl

        # Инициализируем сессию
        self._session = requests.Session()

        # Настраиваем connection pooling
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=0,  # Ретраи управляются через плагин
        )
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

        # Настраиваем параметры сессии
        self._session.headers.update(self._headers)
        self._session.max_redirects = max_redirects

        # Плагины и обработчик ошибок
        self._plugins: List[Plugin] = []
        self._error_handler = ErrorHandler()

        # Флаг инициализации для immutability
        self._initialized = True

    def __setattr__(self, name: str, value: Any):
        """
        Защита от изменения конфигурации после инициализации.
        Обеспечивает потокобезопасность.
        """
        if hasattr(self, "_initialized") and self._initialized:
            if not name.startswith("_"):
                raise RuntimeError(
                    f"Cannot modify attribute '{name}' after client initialization. "
                    "Create a new client instance with different configuration."
                )
        super().__setattr__(name, value)

    def __enter__(self):
        """Поддержка контекстного менеджера"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие сессии при выходе из контекста"""
        self.close()
        return False

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

    def _execute_on_error(self, exception: Exception, **kwargs: Any) -> None:
        """
        Выполняет on_error хуки всех плагинов.

        Args:
            exception: Исключение которое произошло
            **kwargs: Дополнительные параметры
        """
        for plugin in self._plugins:
            try:
                # ВАЖНО: передаем method и url в kwargs
                plugin.on_error(exception, **kwargs)
            except Exception as plugin_error:
                # Логируем ошибку плагина, но не прерываем выполнение
                print(f"Plugin {plugin.__class__.__name__} error in on_error: {plugin_error}")

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
        return f"{self._base_url}/{endpoint}"

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> requests.Response:
        """
        Выполняет HTTP запрос с обработкой через плагины.

        Args:
            method: HTTP метод
            endpoint: Endpoint или полный URL
            **kwargs: Дополнительные параметры запроса

        Returns:
            Объект Response

        Raises:
            HTTPClientException: При ошибках выполнения запроса
        """
        url = self._build_url(endpoint)

        try:
            # Выполняем before_request хуки
            kwargs = self._execute_before_request(method, url, **kwargs)

            # НОВОЕ: Проверяем наличие закэшированного ответа
            if "_cached_response" in kwargs:
                cached_response = kwargs.pop("_cached_response")
                # Создаем mock request объект
                cached_response.request = type(
                    "Request",
                    (),
                    {"method": method, "url": url, "_cache_key": kwargs.get("_cache_key")},
                )()
                return cached_response

            # Устанавливаем прокси если не переопределены в kwargs
            if "proxies" not in kwargs and self._proxies:
                kwargs["proxies"] = self._proxies

            # Устанавливаем timeout если не переопределен
            if "timeout" not in kwargs:
                kwargs["timeout"] = self._timeout

            # Устанавливаем verify если не переопределен
            if "verify" not in kwargs:
                kwargs["verify"] = self._verify_ssl

            # Удаляем ВСЕ служебные параметры перед запросом
            cache_key = kwargs.pop("_cache_key", None)
            monitoring_request_id = kwargs.pop("_monitoring_request_id", None)  # НОВОЕ
            start_time = kwargs.pop("_start_time", None)  # Для MonitoringPlugin
            req_method = kwargs.pop("_method", None)  # Для MonitoringPlugin
            req_url = kwargs.pop("_url", None)  # Для MonitoringPlugin

            # Выполняем запрос через сессию
            response = self._session.request(method, url, **kwargs)

            # Сохраняем служебные параметры в request для использования в after_response
            if cache_key:
                response.request._cache_key = cache_key
            if monitoring_request_id:  # НОВОЕ
                response.request._monitoring_request_id = monitoring_request_id
            if start_time:  # Для MonitoringPlugin
                response.request._start_time = start_time
            if req_method:  # Для MonitoringPlugin
                response.request._method = req_method
            if req_url:  # Для MonitoringPlugin
                response.request._url = req_url

            # Проверяем статус код
            response.raise_for_status()

            # Выполняем after_response хуки
            response = self._execute_after_response(response)

            return response

        except RequestException as e:
            # ИСПРАВЛЕНО: Передаем method и url в on_error
            self._execute_on_error(e, method=method, url=url)

            # Обрабатываем ошибку через ErrorHandler
            self._error_handler.handle_request_exception(e, url, self._timeout)

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
    def base_url(self) -> str:
        """Возвращает базовый URL"""
        return self._base_url

    @property
    def timeout(self) -> int:
        """Возвращает текущий таймаут"""
        return self._timeout
