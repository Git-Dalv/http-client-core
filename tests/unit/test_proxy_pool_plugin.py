"""
Тесты для ProxyPoolPlugin.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
import time

from http_client.plugins.proxy_pool_plugin import ProxyPoolPlugin
from http_client.utils.proxy_manager import ProxyPool, ProxyInfo


class TestProxyPoolPluginInit:
    """Тесты инициализации плагина"""

    def test_init_default(self):
        """Тест инициализации с параметрами по умолчанию"""
        plugin = ProxyPoolPlugin()

        assert plugin._pool is not None
        assert plugin._retry_on_proxy_error is True
        assert plugin._max_retries == 3
        assert plugin._country_filter is None
        assert plugin._proxy_type_filter is None
        assert plugin._plugin_requests == 0

    def test_init_with_pool(self):
        """Тест инициализации с существующим пулом"""
        pool = ProxyPool()
        pool.add_proxy("proxy.com", 8080)

        plugin = ProxyPoolPlugin(pool=pool)

        assert plugin._pool is pool
        assert len(plugin._pool) == 1

    def test_init_with_filters(self):
        """Тест инициализации с фильтрами"""
        plugin = ProxyPoolPlugin(
            country_filter="US",
            proxy_type_filter="http"
        )

        assert plugin._country_filter == "US"
        assert plugin._proxy_type_filter == "http"

    def test_init_with_custom_retry_settings(self):
        """Тест инициализации с настройками повторов"""
        plugin = ProxyPoolPlugin(
            retry_on_proxy_error=False,
            max_retries=5
        )

        assert plugin._retry_on_proxy_error is False
        assert plugin._max_retries == 5


class TestProxyPoolPluginFromList:
    """Тесты создания плагина из списка"""

    def test_from_list_basic(self):
        """Тест создания из простого списка"""
        proxies = [
            "proxy1.com:8080",
            "proxy2.com:1080",
        ]

        plugin = ProxyPoolPlugin.from_list(proxies)

        assert len(plugin._pool) == 2

    def test_from_list_with_auth(self):
        """Тест создания со списком с авторизацией"""
        proxies = [
            "user:pass@proxy1.com:8080",
            "proxy2.com:1080",
        ]

        plugin = ProxyPoolPlugin.from_list(proxies)

        assert len(plugin._pool) == 2

    def test_from_list_with_proxy_type(self):
        """Тест создания с указанием типа прокси"""
        proxies = ["proxy.com:8080"]

        plugin = ProxyPoolPlugin.from_list(
            proxies,
            proxy_type="socks5"
        )

        proxy = plugin._pool.get_proxy()
        assert proxy.proxy_type == "socks5"

    def test_from_list_with_rotation_strategy(self):
        """Тест создания с указанием стратегии"""
        proxies = ["proxy1.com:8080", "proxy2.com:8080"]

        plugin = ProxyPoolPlugin.from_list(
            proxies,
            rotation_strategy="random"
        )

        assert plugin._pool._rotation_strategy == "random"


class TestProxyPoolPluginBeforeRequest:
    """Тесты before_request хука"""

    def test_sets_proxy(self):
        """Тест установки прокси"""
        plugin = ProxyPoolPlugin()
        plugin.add_proxy("proxy.com", 8080)

        kwargs = plugin.before_request("GET", "http://example.com")

        assert "proxies" in kwargs
        assert "http" in kwargs["proxies"]
        assert "proxy.com:8080" in kwargs["proxies"]["http"]

    def test_raises_if_no_proxies(self):
        """Тест ошибки если нет прокси"""
        plugin = ProxyPoolPlugin()

        with pytest.raises(RuntimeError, match="No available proxies"):
            plugin.before_request("GET", "http://example.com")

    def test_increments_request_count(self):
        """Тест инкремента счетчика запросов"""
        plugin = ProxyPoolPlugin()
        plugin.add_proxy("proxy.com", 8080)

        assert plugin._plugin_requests == 0

        plugin.before_request("GET", "http://example.com")
        assert plugin._plugin_requests == 1

        plugin.before_request("POST", "http://example.com")
        assert plugin._plugin_requests == 2

    def test_stores_current_proxy(self):
        """Тест сохранения текущего прокси"""
        plugin = ProxyPoolPlugin()
        plugin.add_proxy("proxy.com", 8080)

        assert plugin._current_proxy is None

        plugin.before_request("GET", "http://example.com")

        assert plugin._current_proxy is not None
        assert plugin._current_proxy.host == "proxy.com"

    def test_stores_request_start_time(self):
        """Тест сохранения времени начала запроса"""
        plugin = ProxyPoolPlugin()
        plugin.add_proxy("proxy.com", 8080)

        assert plugin._request_start_time is None

        before_time = time.time()
        plugin.before_request("GET", "http://example.com")
        after_time = time.time()

        assert plugin._request_start_time is not None
        assert before_time <= plugin._request_start_time <= after_time

    def test_respects_country_filter(self):
        """Тест фильтрации по стране"""
        plugin = ProxyPoolPlugin(country_filter="US")
        plugin.add_proxy("proxy1.com", 8080, country="US")
        plugin.add_proxy("proxy2.com", 8080, country="UK")

        # Должен выбрать только US прокси
        kwargs = plugin.before_request("GET", "http://example.com")

        assert "proxy1.com" in kwargs["proxies"]["http"]

    def test_respects_proxy_type_filter(self):
        """Тест фильтрации по типу"""
        plugin = ProxyPoolPlugin(proxy_type_filter="socks5")
        plugin.add_proxy("proxy1.com", 8080, proxy_type="http")
        plugin.add_proxy("proxy2.com", 1080, proxy_type="socks5")

        kwargs = plugin.before_request("GET", "http://example.com")

        assert "socks5" in kwargs["proxies"]["http"]


class TestProxyPoolPluginAfterResponse:
    """Тесты after_response хука"""

    def test_records_success(self):
        """Тест записи успешного запроса"""
        plugin = ProxyPoolPlugin()
        proxy_info = plugin.add_proxy("proxy.com", 8080)

        # Симулируем запрос
        plugin.before_request("GET", "http://example.com")
        time.sleep(0.1)  # Небольшая задержка

        # Создаем mock ответ
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200

        # Обрабатываем ответ
        result = plugin.after_response(mock_response)

        assert result is mock_response
        assert proxy_info.success_count == 1
        assert proxy_info.total_response_time > 0

    def test_clears_current_proxy(self):
        """Тест очистки текущего прокси"""
        plugin = ProxyPoolPlugin()
        plugin.add_proxy("proxy.com", 8080)

        plugin.before_request("GET", "http://example.com")
        assert plugin._current_proxy is not None

        mock_response = Mock(spec=requests.Response)
        plugin.after_response(mock_response)

        assert plugin._current_proxy is None
        assert plugin._request_start_time is None

    def test_handles_missing_current_proxy(self):
        """Тест обработки отсутствия текущего прокси"""
        plugin = ProxyPoolPlugin()

        mock_response = Mock(spec=requests.Response)

        # Не должно выбросить исключение
        result = plugin.after_response(mock_response)
        assert result is mock_response


class TestProxyPoolPluginOnError:
    """Тесты on_error хука"""

    def test_records_failure(self):
        """Тест записи ошибки"""
        plugin = ProxyPoolPlugin()
        proxy_info = plugin.add_proxy("proxy.com", 8080)

        # Симулируем запрос
        plugin.before_request("GET", "http://example.com")

        # Симулируем ошибку
        error = requests.exceptions.ProxyError("Proxy error")
        plugin.on_error(error)

        assert proxy_info.failure_count == 1
        assert plugin._plugin_failures == 1

    def test_clears_current_proxy_on_error(self):
        """Тест очистки текущего прокси при ошибке"""
        plugin = ProxyPoolPlugin()
        plugin.add_proxy("proxy.com", 8080)

        plugin.before_request("GET", "http://example.com")
        assert plugin._current_proxy is not None

        error = Exception("Test error")
        plugin.on_error(error)

        assert plugin._current_proxy is None
        assert plugin._request_start_time is None

    def test_handles_missing_current_proxy_on_error(self):
        """Тест обработки ошибки без текущего прокси"""
        plugin = ProxyPoolPlugin()

        error = Exception("Test error")

        # Не должно выбросить исключение
        plugin.on_error(error)


class TestProxyPoolPluginProxyManagement:
    """Тесты управления прокси"""

    def test_add_proxy(self):
        """Тест добавления прокси"""
        plugin = ProxyPoolPlugin()

        proxy_info = plugin.add_proxy("proxy.com", 8080)

        assert len(plugin._pool) == 1
        assert proxy_info.host == "proxy.com"
        assert proxy_info.port == 8080

    def test_add_proxy_with_auth(self):
        """Тест добавления прокси с авторизацией"""
        plugin = ProxyPoolPlugin()

        proxy_info = plugin.add_proxy(
            "proxy.com", 8080,
            username="user",
            password="pass"
        )

        assert proxy_info.username == "user"
        assert proxy_info.password == "pass"

    def test_add_proxy_with_metadata(self):
        """Тест добавления прокси с метаданными"""
        plugin = ProxyPoolPlugin()

        proxy_info = plugin.add_proxy(
            "proxy.com", 8080,
            country="US",
            region="California"
        )

        assert proxy_info.country == "US"
        assert proxy_info.region == "California"

    def test_add_proxies_from_list(self):
        """Тест добавления списка прокси"""
        plugin = ProxyPoolPlugin()

        proxies = [
            "proxy1.com:8080",
            "proxy2.com:1080",
            "user:pass@proxy3.com:3128"
        ]

        count = plugin.add_proxies_from_list(proxies)

        assert count == 3
        assert len(plugin._pool) == 3

    def test_remove_proxy(self):
        """Тест удаления прокси"""
        plugin = ProxyPoolPlugin()
        plugin.add_proxy("proxy.com", 8080)

        assert len(plugin._pool) == 1

        result = plugin.remove_proxy("proxy.com", 8080)

        assert result is True
        assert len(plugin._pool) == 0

    def test_remove_nonexistent_proxy(self):
        """Тест удаления несуществующего прокси"""
        plugin = ProxyPoolPlugin()

        result = plugin.remove_proxy("nonexistent.com", 8080)

        assert result is False

    def test_clear_pool(self):
        """Тест очистки пула"""
        plugin = ProxyPoolPlugin()
        plugin.add_proxy("proxy1.com", 8080)
        plugin.add_proxy("proxy2.com", 1080)

        assert len(plugin._pool) == 2

        plugin.clear_pool()

        assert len(plugin._pool) == 0


class TestProxyPoolPluginStats:
    """Тесты статистики"""

    def test_get_stats(self):
        """Тест получения статистики"""
        plugin = ProxyPoolPlugin(
            country_filter="US",
            retry_on_proxy_error=False
        )
        plugin.add_proxy("proxy.com", 8080)

        stats = plugin.get_stats()

        assert "plugin" in stats
        assert "pool" in stats
        assert "filters" in stats
        assert "settings" in stats

        assert stats["plugin"]["requests"] == 0
        assert stats["filters"]["country"] == "US"
        assert stats["settings"]["retry_on_error"] is False

    def test_get_proxy_stats(self):
        """Тест получения статистики по прокси"""
        plugin = ProxyPoolPlugin()
        plugin.add_proxy("proxy1.com", 8080, country="US")
        plugin.add_proxy("proxy2.com", 1080, country="UK")

        stats = plugin.get_proxy_stats()

        assert len(stats) == 2
        assert stats[0]["host"] == "proxy1.com"
        assert stats[0]["country"] == "US"
        assert stats[1]["host"] == "proxy2.com"

    def test_reset_stats(self):
        """Тест сброса статистики"""
        plugin = ProxyPoolPlugin()
        plugin.add_proxy("proxy.com", 8080)

        # Делаем запрос
        plugin.before_request("GET", "http://example.com")

        assert plugin._plugin_requests == 1

        # Сбрасываем
        plugin.reset_stats()

        assert plugin._plugin_requests == 0
        assert plugin._plugin_retries == 0
        assert plugin._plugin_failures == 0


class TestProxyPoolPluginUtilities:
    """Тесты утилит"""

    def test_pool_property(self):
        """Тест доступа к пулу"""
        plugin = ProxyPoolPlugin()

        # Проверяем что пул существует и это ProxyPool
        assert plugin.pool is not None
        assert isinstance(plugin.pool, ProxyPool)

        # Проверяем что можем добавлять прокси через пул
        plugin.pool.add_proxy("test.com", 8080)
        assert len(plugin.pool) == 1

    def test_get_current_proxy(self):
        """Тест получения текущего прокси"""
        plugin = ProxyPoolPlugin()
        plugin.add_proxy("proxy.com", 8080)

        assert plugin.get_current_proxy() is None

        plugin.before_request("GET", "http://example.com")

        current = plugin.get_current_proxy()
        assert current is not None
        assert current.host == "proxy.com"

    def test_change_rotation_strategy(self):
        """Тест изменения стратегии ротации"""
        plugin = ProxyPoolPlugin()

        assert plugin._pool._rotation_strategy == "round_robin"

        plugin.change_rotation_strategy("random")

        assert plugin._pool._rotation_strategy == "random"

    def test_set_filters(self):
        """Тест установки фильтров"""
        plugin = ProxyPoolPlugin()

        assert plugin._country_filter is None
        assert plugin._proxy_type_filter is None

        plugin.set_filters(country="US", proxy_type="socks5")

        assert plugin._country_filter == "US"
        assert plugin._proxy_type_filter == "socks5"

    def test_len(self):
        """Тест __len__"""
        plugin = ProxyPoolPlugin()

        assert len(plugin) == 0

        plugin.add_proxy("proxy1.com", 8080)
        plugin.add_proxy("proxy2.com", 1080)

        assert len(plugin) == 2

    def test_repr(self):
        """Тест __repr__"""
        plugin = ProxyPoolPlugin()
        plugin.add_proxy("proxy.com", 8080)
        plugin.before_request("GET", "http://example.com")

        repr_str = repr(plugin)

        assert "ProxyPoolPlugin" in repr_str
        assert "proxies=1" in repr_str
        assert "requests=1" in repr_str


class TestProxyPoolPluginIntegration:
    """Интеграционные тесты"""

    def test_full_request_cycle(self):
        """Тест полного цикла запроса"""
        plugin = ProxyPoolPlugin()
        proxy_info = plugin.add_proxy("proxy.com", 8080)

        # Before request
        kwargs = plugin.before_request("GET", "http://example.com")
        assert "proxies" in kwargs

        # Simulate request
        time.sleep(0.05)

        # After response
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        plugin.after_response(mock_response)

        # Check stats
        assert proxy_info.success_count == 1
        assert proxy_info.total_response_time > 0
        assert plugin._plugin_requests == 1

    def test_error_handling_cycle(self):
        """Тест цикла обработки ошибки"""
        plugin = ProxyPoolPlugin()
        proxy_info = plugin.add_proxy("proxy.com", 8080)

        # Before request
        plugin.before_request("GET", "http://example.com")

        # Error occurs
        error = requests.exceptions.ProxyError("Proxy failed")
        plugin.on_error(error)

        # Check stats
        assert proxy_info.failure_count == 1
        assert plugin._plugin_failures == 1

    def test_round_robin_rotation(self):
        """Тест round-robin ротации"""
        plugin = ProxyPoolPlugin()
        plugin.add_proxy("proxy1.com", 8080)
        plugin.add_proxy("proxy2.com", 8080)
        plugin.add_proxy("proxy3.com", 8080)

        proxies_used = []

        for _ in range(6):  # 2 полных цикла
            kwargs = plugin.before_request("GET", "http://example.com")
            proxy_url = kwargs["proxies"]["http"]
            proxies_used.append(proxy_url)

            # Cleanup для следующей итерации
            plugin._current_proxy = None

        # Проверяем что прокси чередуются
        assert len(set(proxies_used)) == 3

        # Проверяем что паттерн повторяется
        assert proxies_used[0] == proxies_used[3]
        assert proxies_used[1] == proxies_used[4]
        assert proxies_used[2] == proxies_used[5]