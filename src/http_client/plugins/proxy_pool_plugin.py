"""
Плагин для автоматической ротации прокси серверов.

Использует ProxyPool для управления пулом прокси и автоматической
ротации при каждом запросе. Поддерживает различные стратегии
ротации и автоматическую обработку ошибок прокси.
"""

from typing import Any, Dict, Optional
import logging
import time
import requests

from .plugin import Plugin
from ..utils.proxy_manager import ProxyPool, ProxyInfo, ProxyType, RotationStrategy

logger = logging.getLogger(__name__)


class ProxyPoolPlugin(Plugin):
    """
    Плагин для автоматической ротации прокси.

    Example:
        # Создание пула и плагина
        pool = ProxyPool(rotation_strategy="round_robin")
        pool.add_proxy("proxy1.com", 8080)
        pool.add_proxy("proxy2.com", 1080, proxy_type="socks5")

        plugin = ProxyPoolPlugin(pool)
        client.add_plugin(plugin)

        # Запросы автоматически используют прокси
        response = client.get("/endpoint")

        # Или создать плагин с автоматическим пулом
        plugin = ProxyPoolPlugin.from_list([
            "proxy1.com:8080",
            "proxy2.com:1080"
        ])
    """

    def __init__(
            self,
            pool: Optional[ProxyPool] = None,
            retry_on_proxy_error: bool = True,
            max_retries: int = 3,
            country_filter: Optional[str] = None,
            proxy_type_filter: Optional[ProxyType] = None,
    ):
        """
        Инициализация плагина.

        Args:
            pool: ProxyPool объект (если None, создается пустой)
            retry_on_proxy_error: Повторять запрос с другим прокси при ошибке
            max_retries: Максимальное количество повторов
            country_filter: Фильтр по стране (применяется при выборе прокси)
            proxy_type_filter: Фильтр по типу прокси
        """
        self._pool = pool or ProxyPool()
        self._retry_on_proxy_error = retry_on_proxy_error
        self._max_retries = max_retries
        self._country_filter = country_filter
        self._proxy_type_filter = proxy_type_filter

        # Текущий прокси для запроса
        self._current_proxy: Optional[ProxyInfo] = None
        self._request_start_time: Optional[float] = None

        # Статистика плагина
        self._plugin_requests = 0
        self._plugin_retries = 0
        self._plugin_failures = 0

    @classmethod
    def from_list(
            cls,
            proxies: list,
            proxy_type: ProxyType = "http",
            rotation_strategy: RotationStrategy = "round_robin",
            check_on_add: bool = False,
            **kwargs,
    ) -> "ProxyPoolPlugin":
        """
        Создает плагин из списка прокси строк.

        Args:
            proxies: Список прокси в формате "host:port" или "user:pass@host:port"
            proxy_type: Тип прокси для всех
            rotation_strategy: Стратегия ротации
            check_on_add: Проверять прокси при добавлении
            **kwargs: Дополнительные параметры для ProxyPoolPlugin

        Returns:
            ProxyPoolPlugin объект

        Example:
            plugin = ProxyPoolPlugin.from_list([
                "proxy1.com:8080",
                "user:pass@proxy2.com:1080"
            ])
        """
        pool = ProxyPool(
            rotation_strategy=rotation_strategy,
            check_on_add=check_on_add,
        )
        pool.add_proxies_from_list(proxies, proxy_type=proxy_type)

        return cls(pool=pool, **kwargs)

    def before_request(
            self,
            method: str,
            url: str,
            **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Устанавливает прокси перед запросом.

        Args:
            method: HTTP метод
            url: URL запроса
            **kwargs: Параметры запроса

        Returns:
            Обновленные параметры запроса с прокси

        Raises:
            RuntimeError: Если нет доступных прокси
        """
        # Получаем прокси из пула
        proxy = self._pool.get_proxy(
            country=self._country_filter,
            proxy_type=self._proxy_type_filter,
        )

        if not proxy:
            raise RuntimeError(
                "No available proxies in pool. "
                "Add proxies using pool.add_proxy() or check proxy health."
            )

        # Сохраняем для after_response и on_error
        self._current_proxy = proxy
        self._request_start_time = time.time()

        # Устанавливаем прокси в kwargs
        kwargs["proxies"] = proxy.to_dict()

        # Увеличиваем счетчик
        self._plugin_requests += 1

        return kwargs

    def after_response(self, response: requests.Response) -> requests.Response:
        """
        Записывает успешный запрос через прокси.

        Args:
            response: Объект ответа

        Returns:
            Неизмененный ответ
        """
        if self._current_proxy and self._request_start_time:
            # Вычисляем время ответа
            response_time = time.time() - self._request_start_time

            # Записываем успех
            self._pool.record_success(self._current_proxy, response_time)

            # Очищаем состояние
            self._current_proxy = None
            self._request_start_time = None

        return response

    def on_error(self, error: Exception, **kwargs: Any) -> None:
        """
        Обрабатывает ошибку прокси.

        Args:
            error: Исключение
            **kwargs: Дополнительные параметры
        """
        if self._current_proxy:
            # Записываем ошибку
            self._pool.record_failure(self._current_proxy)
            self._plugin_failures += 1

            # Очищаем состояние
            self._current_proxy = None
            self._request_start_time = None

    # ==================== Управление пулом ====================

    def add_proxy(
            self,
            host: str,
            port: int,
            proxy_type: ProxyType = "http",
            username: Optional[str] = None,
            password: Optional[str] = None,
            **metadata,
    ) -> ProxyInfo:
        """
        Добавляет прокси в пул.

        Args:
            host: Хост прокси
            port: Порт прокси
            proxy_type: Тип прокси
            username: Имя пользователя
            password: Пароль
            **metadata: Дополнительные метаданные

        Returns:
            ProxyInfo объект

        Example:
            plugin.add_proxy("proxy.com", 8080)
            plugin.add_proxy("proxy.com", 1080, proxy_type="socks5", country="US")
        """
        return self._pool.add_proxy(
            host=host,
            port=port,
            proxy_type=proxy_type,
            username=username,
            password=password,
            **metadata,
        )

    def add_proxies_from_list(
            self,
            proxies: list,
            proxy_type: ProxyType = "http",
            check_all: bool = False,
    ) -> int:
        """
        Добавляет несколько прокси из списка.

        Args:
            proxies: Список прокси строк
            proxy_type: Тип прокси
            check_all: Проверить все прокси

        Returns:
            Количество добавленных прокси
        """
        return self._pool.add_proxies_from_list(
            proxies=proxies,
            proxy_type=proxy_type,
            check_all=check_all,
        )

    def remove_proxy(self, host: str, port: int) -> bool:
        """
        Удаляет прокси из пула.

        Args:
            host: Хост прокси
            port: Порт прокси

        Returns:
            True если прокси был удален
        """
        return self._pool.remove_proxy(host, port)

    def clear_pool(self):
        """Удаляет все прокси из пула"""
        self._pool.clear()

    # ==================== Проверка прокси ====================

    def check_all_proxies(self) -> Dict[str, int]:
        """
        Проверяет все прокси в пуле.

        Returns:
            Словарь с результатами проверки

        Example:
            results = plugin.check_all_proxies()
            print(f"Working: {results['working']}/{results['total']}")
        """
        return self._pool.check_all_proxies()

    # ==================== Статистика ====================

    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику плагина и пула.

        Returns:
            Словарь со статистикой

        Example:
            stats = plugin.get_stats()
            print(f"Total proxies: {stats['pool']['total_proxies']}")
            print(f"Plugin requests: {stats['plugin']['requests']}")
        """
        pool_stats = self._pool.get_stats()

        return {
            "plugin": {
                "requests": self._plugin_requests,
                "retries": self._plugin_retries,
                "failures": self._plugin_failures,
            },
            "pool": pool_stats,
            "filters": {
                "country": self._country_filter,
                "proxy_type": self._proxy_type_filter,
            },
            "settings": {
                "retry_on_error": self._retry_on_proxy_error,
                "max_retries": self._max_retries,
            }
        }

    def get_proxy_stats(self) -> list:
        """
        Возвращает статистику по каждому прокси.

        Returns:
            Список словарей с информацией о прокси
        """
        return self._pool.get_proxy_stats()

    def reset_stats(self):
        """Сбрасывает статистику плагина (не трогает пул)"""
        self._plugin_requests = 0
        self._plugin_retries = 0
        self._plugin_failures = 0

    # ==================== Утилиты ====================

    @property
    def pool(self) -> ProxyPool:
        """Возвращает объект пула для прямого доступа"""
        return self._pool

    def get_current_proxy(self) -> Optional[ProxyInfo]:
        """Возвращает текущий используемый прокси (во время запроса)"""
        return self._current_proxy

    def change_rotation_strategy(self, strategy: RotationStrategy):
        """
        Изменяет стратегию ротации.

        Args:
            strategy: Новая стратегия
        """
        self._pool._rotation_strategy = strategy

    def set_filters(
            self,
            country: Optional[str] = None,
            proxy_type: Optional[ProxyType] = None,
    ):
        """
        Устанавливает фильтры для выбора прокси.

        Args:
            country: Фильтр по стране (None = убрать фильтр)
            proxy_type: Фильтр по типу (None = убрать фильтр)

        Example:
            plugin.set_filters(country="US")
            plugin.set_filters(proxy_type="socks5")
            plugin.set_filters(country="US", proxy_type="http")
        """
        self._country_filter = country
        self._proxy_type_filter = proxy_type

    def __len__(self) -> int:
        """Возвращает количество прокси в пуле"""
        return len(self._pool)

    def __repr__(self) -> str:
        """Строковое представление плагина"""
        return (
            f"ProxyPoolPlugin(proxies={len(self._pool)}, "
            f"requests={self._plugin_requests}, "
            f"strategy='{self._pool._rotation_strategy}')"
        )