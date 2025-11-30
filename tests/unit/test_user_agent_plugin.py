"""
Тесты для UserAgentPlugin.
"""

import pytest
from unittest.mock import Mock, patch
import requests

from http_client.plugins.user_agent_plugin import UserAgentPlugin
from http_client.utils.user_agents import CHROME_USER_AGENTS


class TestUserAgentPluginInit:
    """Тесты инициализации плагина"""

    def test_init_default(self):
        """Тест инициализации с параметрами по умолчанию"""
        plugin = UserAgentPlugin()

        assert plugin._strategy == "random"
        assert plugin._browser is None
        assert plugin._os is None
        assert plugin._generator is not None
        assert plugin._request_count == 0
        assert plugin._last_user_agent is None

    def test_init_with_filters(self):
        """Тест инициализации с фильтрами"""
        plugin = UserAgentPlugin(
            strategy="weighted",
            browser="chrome",
            os="windows"
        )

        assert plugin._strategy == "weighted"
        assert plugin._browser == "chrome"
        assert plugin._os == "windows"

    def test_init_fixed_strategy(self):
        """Тест инициализации с фиксированным UA"""
        custom_ua = "Mozilla/5.0 Custom"
        plugin = UserAgentPlugin(
            strategy="fixed",
            user_agent=custom_ua
        )

        assert plugin._strategy == "fixed"
        assert plugin._fixed_user_agent == custom_ua
        assert plugin._generator is None

    def test_init_invalid_strategy(self):
        """Тест с невалидной стратегией"""
        with pytest.raises(ValueError, match="Invalid strategy"):
            UserAgentPlugin(strategy="invalid")

    def test_init_fixed_without_user_agent(self):
        """Тест fixed стратегии без user_agent"""
        with pytest.raises(ValueError, match="user_agent must be provided"):
            UserAgentPlugin(strategy="fixed")

    def test_init_invalid_filters(self):
        """Тест с невалидными фильтрами"""
        with pytest.raises(ValueError):
            UserAgentPlugin(browser="nonexistent", os="fake")


class TestUserAgentPluginStrategies:
    """Тесты различных стратегий ротации"""

    def test_random_strategy(self):
        """Тест random стратегии"""
        plugin = UserAgentPlugin(strategy="random")

        # Делаем несколько запросов
        user_agents = set()
        for _ in range(10):
            kwargs = plugin.before_request("GET", "http://example.com")
            ua = kwargs["headers"]["User-Agent"]
            user_agents.add(ua)

        # Должны быть разные UA (с высокой вероятностью)
        assert len(user_agents) > 1

    def test_weighted_strategy(self):
        """Тест weighted стратегии"""
        plugin = UserAgentPlugin(strategy="weighted", browser="chrome")

        # Делаем много запросов
        user_agents = []
        for _ in range(100):
            kwargs = plugin.before_request("GET", "http://example.com")
            ua = kwargs["headers"]["User-Agent"]
            user_agents.append(ua)

        # Популярные UA должны встречаться чаще
        # Проверяем что есть разнообразие
        assert len(set(user_agents)) > 1

    def test_round_robin_strategy(self):
        """Тест round_robin стратегии"""
        plugin = UserAgentPlugin(
            strategy="round_robin",
            browser="chrome",
            os="windows"
        )

        # Получаем доступные UA
        available = plugin.get_available_user_agents()

        # Делаем запросы = количеству доступных UA
        user_agents = []
        for _ in range(len(available)):
            kwargs = plugin.before_request("GET", "http://example.com")
            ua = kwargs["headers"]["User-Agent"]
            user_agents.append(ua)

        # Все UA должны быть уникальными (один цикл)
        assert len(set(user_agents)) == len(available)

        # Следующий запрос должен повторить первый UA
        kwargs = plugin.before_request("GET", "http://example.com")
        next_ua = kwargs["headers"]["User-Agent"]
        assert next_ua == user_agents[0]

        def test_fixed_strategy(self):
            """Тест fixed стратегии"""
            custom_ua = "Mozilla/5.0 CustomBot"
            plugin = UserAgentPlugin(strategy="fixed", user_agent=custom_ua)

            # Все запросы должны использовать один UA
            for _ in range(5):
                kwargs = plugin.before_request("GET", "http://example.com")
                assert kwargs["headers"]["User-Agent"] == custom_ua


    class TestUserAgentPluginBeforeRequest:
        """Тесты before_request хука"""

        def test_sets_user_agent_header(self):
            """Тест установки User-Agent заголовка"""
            plugin = UserAgentPlugin(strategy="fixed", user_agent="TestUA")

            kwargs = plugin.before_request("GET", "http://example.com")

            assert "headers" in kwargs
            assert "User-Agent" in kwargs["headers"]
            assert kwargs["headers"]["User-Agent"] == "TestUA"

        def test_preserves_existing_headers(self):
            """Тест сохранения существующих заголовков"""
            plugin = UserAgentPlugin(strategy="fixed", user_agent="TestUA")

            kwargs = {
                "headers": {
                    "Authorization": "Bearer token",
                    "Content-Type": "application/json"
                }
            }

            result = plugin.before_request("GET", "http://example.com", **kwargs)

            assert result["headers"]["Authorization"] == "Bearer token"
            assert result["headers"]["Content-Type"] == "application/json"
            assert result["headers"]["User-Agent"] == "TestUA"

        def test_overwrites_existing_user_agent(self):
            """Тест перезаписи существующего User-Agent"""
            plugin = UserAgentPlugin(strategy="fixed", user_agent="NewUA")

            kwargs = {
                "headers": {
                    "User-Agent": "OldUA"
                }
            }

            result = plugin.before_request("GET", "http://example.com", **kwargs)

            assert result["headers"]["User-Agent"] == "NewUA"

        def test_handles_none_headers(self):
            """Тест обработки None в headers"""
            plugin = UserAgentPlugin(strategy="fixed", user_agent="TestUA")

            kwargs = {"headers": None}
            result = plugin.before_request("GET", "http://example.com", **kwargs)

            assert result["headers"]["User-Agent"] == "TestUA"

        def test_increments_request_count(self):
            """Тест инкремента счетчика запросов"""
            plugin = UserAgentPlugin()

            assert plugin._request_count == 0

            plugin.before_request("GET", "http://example.com")
            assert plugin._request_count == 1

            plugin.before_request("POST", "http://example.com")
            assert plugin._request_count == 2

        def test_updates_last_user_agent(self):
            """Тест обновления последнего UA"""
            plugin = UserAgentPlugin(strategy="fixed", user_agent="TestUA")

            assert plugin._last_user_agent is None

            plugin.before_request("GET", "http://example.com")
            assert plugin._last_user_agent == "TestUA"


    class TestUserAgentPluginAfterResponse:
        """Тесты after_response хука"""

        def test_returns_response_unchanged(self):
            """Тест что ответ не изменяется"""
            plugin = UserAgentPlugin()

            mock_response = Mock(spec=requests.Response)
            mock_response.status_code = 200

            result = plugin.after_response(mock_response)

            assert result is mock_response
            assert result.status_code == 200


    class TestUserAgentPluginOnError:
        """Тесты on_error хука"""

        def test_does_not_raise_on_error(self):
            """Тест что плагин не выбрасывает исключения"""
            plugin = UserAgentPlugin()

            error = Exception("Test error")

            # Не должно выбросить исключение
            plugin.on_error(error, method="GET", url="http://example.com")


    class TestUserAgentPluginStats:
        """Тесты статистики"""

        def test_get_stats(self):
            """Тест получения статистики"""
            plugin = UserAgentPlugin(
                strategy="weighted",
                browser="chrome",
                os="windows"
            )

            # Делаем запрос
            plugin.before_request("GET", "http://example.com")

            stats = plugin.get_stats()

            assert stats["request_count"] == 1
            assert stats["last_user_agent"] is not None
            assert stats["strategy"] == "weighted"
            assert stats["browser"] == "chrome"
            assert stats["os"] == "windows"

        def test_reset_stats(self):
            """Тест сброса статистики"""
            plugin = UserAgentPlugin(strategy="round_robin")

            # Делаем несколько запросов
            for _ in range(3):
                plugin.before_request("GET", "http://example.com")

            assert plugin._request_count == 3
            assert plugin._last_user_agent is not None

            # Сбрасываем
            plugin.reset_stats()

            assert plugin._request_count == 0
            assert plugin._last_user_agent is None


    class TestUserAgentPluginPublicMethods:
        """Тесты публичных методов"""

        def test_get_available_user_agents(self):
            """Тест получения доступных UA"""
            plugin = UserAgentPlugin(browser="chrome", os="windows")

            available = plugin.get_available_user_agents()

            assert isinstance(available, list)
            assert len(available) > 0
            assert all(isinstance(ua, str) for ua in available)

        def test_get_available_user_agents_fixed(self):
            """Тест получения UA для fixed стратегии"""
            custom_ua = "Mozilla/5.0 Custom"
            plugin = UserAgentPlugin(strategy="fixed", user_agent=custom_ua)

            available = plugin.get_available_user_agents()

            assert available == [custom_ua]

        def test_change_strategy(self):
            """Тест изменения стратегии"""
            plugin = UserAgentPlugin(strategy="random")

            assert plugin._strategy == "random"

            plugin.change_strategy("weighted")

            assert plugin._strategy == "weighted"

        def test_change_strategy_to_fixed(self):
            """Тест изменения на fixed стратегию"""
            plugin = UserAgentPlugin(strategy="random")

            custom_ua = "Mozilla/5.0 Custom"
            plugin.change_strategy("fixed", user_agent=custom_ua)

            assert plugin._strategy == "fixed"
            assert plugin._fixed_user_agent == custom_ua

        def test_change_strategy_invalid(self):
            """Тест изменения на невалидную стратегию"""
            plugin = UserAgentPlugin()

            with pytest.raises(ValueError, match="Invalid strategy"):
                plugin.change_strategy("invalid")

        def test_change_strategy_fixed_without_ua(self):
            """Тест изменения на fixed без UA"""
            plugin = UserAgentPlugin()

            with pytest.raises(ValueError, match="user_agent must be provided"):
                plugin.change_strategy("fixed")


    class TestUserAgentPluginRepr:
        """Тесты строкового представления"""

        def test_repr(self):
            """Тест __repr__"""
            plugin = UserAgentPlugin(
                strategy="weighted",
                browser="chrome",
                os="windows"
            )

            plugin.before_request("GET", "http://example.com")

            repr_str = repr(plugin)

            assert "UserAgentPlugin" in repr_str
            assert "strategy='weighted'" in repr_str
            assert "browser=chrome" in repr_str
            assert "os=windows" in repr_str
            assert "requests=1" in repr_str


    class TestUserAgentPluginIntegration:
        """Интеграционные тесты"""

        def test_multiple_requests_different_ua(self):
            """Тест что разные запросы получают разные UA"""
            plugin = UserAgentPlugin(strategy="random")

            user_agents = set()
            for _ in range(20):
                kwargs = plugin.before_request("GET", "http://example.com")
                user_agents.add(kwargs["headers"]["User-Agent"])

            # Должно быть хотя бы 2 разных UA
            assert len(user_agents) >= 2

        def test_filter_by_browser(self):
            """Тест фильтрации по браузеру"""
            plugin = UserAgentPlugin(browser="chrome")

            # Все UA должны содержать Chrome
            for _ in range(10):
                kwargs = plugin.before_request("GET", "http://example.com")
                ua = kwargs["headers"]["User-Agent"]
                assert "Chrome" in ua

        def test_filter_by_os(self):
            """Тест фильтрации по ОС"""
            plugin = UserAgentPlugin(os="windows")

            # Все UA должны содержать Windows
            for _ in range(10):
                kwargs = plugin.before_request("GET", "http://example.com")
                ua = kwargs["headers"]["User-Agent"]
                assert "Windows" in ua

        def test_combined_filters(self):
            """Тест комбинированных фильтров"""
            plugin = UserAgentPlugin(browser="firefox", os="linux")

            for _ in range(10):
                kwargs = plugin.before_request("GET", "http://example.com")
                ua = kwargs["headers"]["User-Agent"]
                assert "Firefox" in ua
                assert "Linux" in ua or "X11" in ua