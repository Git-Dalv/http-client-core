"""
Плагин для автоматической ротации User-Agent заголовков.

Поддерживает различные стратегии ротации:
- random: случайный выбор при каждом запросе
- weighted: случайный выбор с учетом популярности
- round_robin: последовательная ротация
- fixed: фиксированный User-Agent

Используется для обхода блокировок и имитации реальных браузеров.
"""

from typing import Any, Dict, Optional
import requests

from .plugin import Plugin
from ..utils.user_agents import (
    UserAgentGenerator,
    BrowserType,
    OSType,
    get_random_user_agent,
)


class UserAgentPlugin(Plugin):
    """
    Плагин для автоматической ротации User-Agent.

    Example:
        # Случайная ротация
        plugin = UserAgentPlugin(strategy="random")
        client.add_plugin(plugin)

        # Только Chrome на Windows
        plugin = UserAgentPlugin(
            strategy="weighted",
            browser="chrome",
            os="windows"
        )

        # Последовательная ротация
        plugin = UserAgentPlugin(strategy="round_robin")

        # Фиксированный User-Agent
        plugin = UserAgentPlugin(
            strategy="fixed",
            user_agent="Mozilla/5.0 ..."
        )
    """

    def __init__(
            self,
            strategy: str = "random",
            browser: Optional[BrowserType] = None,
            os: Optional[OSType] = None,
            user_agent: Optional[str] = None,
    ):
        """
        Инициализация плагина.

        Args:
            strategy: Стратегия ротации:
                - "random": случайный выбор
                - "weighted": с учетом популярности
                - "round_robin": последовательная ротация
                - "fixed": фиксированный UA
            browser: Фильтр по браузеру (None = все)
            os: Фильтр по ОС (None = все)
            user_agent: Фиксированный User-Agent для strategy="fixed"

        Raises:
            ValueError: Если strategy неизвестна или для fixed не указан user_agent
        """
        valid_strategies = {"random", "weighted", "round_robin", "fixed"}
        if strategy not in valid_strategies:
            raise ValueError(
                f"Invalid strategy '{strategy}'. "
                f"Must be one of: {', '.join(valid_strategies)}"
            )

        if strategy == "fixed" and not user_agent:
            raise ValueError("user_agent must be provided for strategy='fixed'")

        self._strategy = strategy
        self._browser = browser
        self._os = os
        self._fixed_user_agent = user_agent

        # Инициализируем генератор (кроме fixed стратегии)
        if strategy != "fixed":
            try:
                self._generator = UserAgentGenerator(
                    browser=browser,
                    os=os,
                )
            except ValueError as e:
                raise ValueError(f"Failed to initialize UserAgentGenerator: {e}")
        else:
            self._generator = None

        # Статистика
        self._request_count = 0
        self._last_user_agent = None

    def before_request(
            self,
            method: str,
            url: str,
            **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Устанавливает User-Agent перед запросом.

        Args:
            method: HTTP метод
            url: URL запроса
            **kwargs: Параметры запроса

        Returns:
            Обновленные параметры запроса с новым User-Agent
        """
        # Получаем headers из kwargs или создаем новый dict
        headers = kwargs.get("headers", {})
        if headers is None:
            headers = {}

        # Генерируем User-Agent по выбранной стратегии
        user_agent = self._get_user_agent()

        # Устанавливаем заголовок
        headers["User-Agent"] = user_agent
        kwargs["headers"] = headers

        # Сохраняем для статистики
        self._last_user_agent = user_agent
        self._request_count += 1

        return kwargs

    def after_response(self, response: requests.Response) -> requests.Response:
        """
        Вызывается после получения ответа.

        Args:
            response: Объект ответа

        Returns:
            Неизмененный ответ
        """
        # Плагин не модифицирует ответ
        return response

    def on_error(self, error: Exception, **kwargs: Any) -> None:
        """
        Вызывается при ошибке запроса.

        Args:
            error: Исключение
            **kwargs: Дополнительные параметры
        """
        # Плагин не обрабатывает ошибки
        pass

    # ==================== Внутренние методы ====================

    def _get_user_agent(self) -> str:
        """
        Возвращает User-Agent согласно выбранной стратегии.

        Returns:
            User-Agent строка
        """
        if self._strategy == "fixed":
            return self._fixed_user_agent

        elif self._strategy == "random":
            return self._generator.random()

        elif self._strategy == "weighted":
            return self._generator.weighted_random()

        elif self._strategy == "round_robin":
            return self._generator.next()

        # Не должно произойти из-за валидации в __init__
        raise RuntimeError(f"Unknown strategy: {self._strategy}")

    # ==================== Публичные методы ====================

    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику работы плагина.

        Returns:
            Словарь со статистикой:
                - request_count: количество запросов
                - last_user_agent: последний использованный UA
                - strategy: текущая стратегия
                - browser: фильтр по браузеру
                - os: фильтр по ОС

        Example:
            stats = plugin.get_stats()
            print(f"Requests: {stats['request_count']}")
            print(f"Last UA: {stats['last_user_agent']}")
        """
        return {
            "request_count": self._request_count,
            "last_user_agent": self._last_user_agent,
            "strategy": self._strategy,
            "browser": self._browser,
            "os": self._os,
        }

    def reset_stats(self):
        """Сбрасывает статистику"""
        self._request_count = 0
        self._last_user_agent = None
        if self._generator and self._strategy == "round_robin":
            self._generator.reset()

    def get_available_user_agents(self) -> list:
        """
        Возвращает список доступных User-Agent строк.

        Returns:
            Список User-Agent строк (для fixed стратегии возвращает [fixed_ua])

        Example:
            plugin = UserAgentPlugin(browser="chrome", os="windows")
            available = plugin.get_available_user_agents()
            print(f"Available: {len(available)} user agents")
        """
        if self._strategy == "fixed":
            return [self._fixed_user_agent]

        return self._generator.get_all()

    def change_strategy(
            self,
            strategy: str,
            user_agent: Optional[str] = None,
    ):
        """
        Изменяет стратегию ротации на лету.

        Args:
            strategy: Новая стратегия
            user_agent: User-Agent для fixed стратегии

        Raises:
            ValueError: Если стратегия невалидна

        Example:
            # Переключаемся с random на round_robin
            plugin.change_strategy("round_robin")

            # Переключаемся на фиксированный UA
            plugin.change_strategy("fixed", user_agent="Mozilla/5.0 ...")
        """
        valid_strategies = {"random", "weighted", "round_robin", "fixed"}
        if strategy not in valid_strategies:
            raise ValueError(
                f"Invalid strategy '{strategy}'. "
                f"Must be one of: {', '.join(valid_strategies)}"
            )

        if strategy == "fixed" and not user_agent:
            raise ValueError("user_agent must be provided for strategy='fixed'")

        self._strategy = strategy

        if strategy == "fixed":
            self._fixed_user_agent = user_agent

        # Сбрасываем round_robin индекс
        if self._generator and strategy == "round_robin":
            self._generator.reset()

    def __repr__(self) -> str:
        """Строковое представление плагина"""
        return (
            f"UserAgentPlugin(strategy='{self._strategy}', "
            f"browser={self._browser}, os={self._os}, "
            f"requests={self._request_count})"
        )