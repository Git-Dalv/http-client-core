"""
Тесты для системы приоритетов плагинов.

Проверяет корректность порядка выполнения плагинов согласно их приоритетам.
"""

import pytest
import requests
from unittest.mock import Mock, patch
from typing import Any, Dict

from http_client.core.http_client import HTTPClient
from http_client.plugins.plugin import Plugin, PluginPriority
from http_client.plugins.base_v2 import PluginV2
from http_client.core.context import RequestContext
from http_client.plugins.auth_plugin import AuthPlugin
from http_client.plugins.cache_plugin import CachePlugin
from http_client.plugins.rate_limit_plugin import RateLimitPlugin
from http_client.plugins.logging_plugin import LoggingPlugin
from http_client.plugins.monitoring_plugin import MonitoringPlugin


# ==================== Test Plugins ====================


class MockPluginFirst(Plugin):
    """Тестовый плагин с приоритетом FIRST."""

    priority = PluginPriority.FIRST

    def __init__(self):
        self.call_order = []

    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        self.call_order.append('MockPluginFirst')
        return kwargs

    def after_response(self, response):
        return response

    def on_error(self, error: Exception, **kwargs) -> bool:
        return False


class MockPluginCache(Plugin):
    """Тестовый плагин с приоритетом CACHE."""

    priority = PluginPriority.CACHE

    def __init__(self):
        self.call_order = []

    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        self.call_order.append('MockPluginCache')
        return kwargs

    def after_response(self, response):
        return response

    def on_error(self, error: Exception, **kwargs) -> bool:
        return False


class MockPluginHigh(Plugin):
    """Тестовый плагин с приоритетом HIGH."""

    priority = PluginPriority.HIGH

    def __init__(self):
        self.call_order = []

    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        self.call_order.append('MockPluginHigh')
        return kwargs

    def after_response(self, response):
        return response

    def on_error(self, error: Exception, **kwargs) -> bool:
        return False


class MockPluginNormal(Plugin):
    """Тестовый плагин с приоритетом NORMAL."""

    priority = PluginPriority.NORMAL

    def __init__(self):
        self.call_order = []

    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        self.call_order.append('MockPluginNormal')
        return kwargs

    def after_response(self, response):
        return response

    def on_error(self, error: Exception, **kwargs) -> bool:
        return False


class MockPluginLast(Plugin):
    """Тестовый плагин с приоритетом LAST."""

    priority = PluginPriority.LAST

    def __init__(self):
        self.call_order = []

    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        self.call_order.append('MockPluginLast')
        return kwargs

    def after_response(self, response):
        return response

    def on_error(self, error: Exception, **kwargs) -> bool:
        return False


class MockPluginNoPriority(Plugin):
    """Тестовый плагин БЕЗ явного приоритета (должен получить default NORMAL=50)."""

    def __init__(self):
        self.call_order = []

    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        self.call_order.append('MockPluginNoPriority')
        return kwargs

    def after_response(self, response):
        return response

    def on_error(self, error: Exception, **kwargs) -> bool:
        return False


class MockPluginCustomPriority(Plugin):
    """Тестовый плагин с кастомным приоритетом."""

    priority = 15  # Между CACHE (10) и HIGH (25)

    def __init__(self):
        self.call_order = []

    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        self.call_order.append('MockPluginCustomPriority')
        return kwargs

    def after_response(self, response):
        return response

    def on_error(self, error: Exception, **kwargs) -> bool:
        return False


# ==================== Test v2 Plugin ====================


class MockPluginV2High(PluginV2):
    """Тестовый PluginV2 с приоритетом HIGH."""

    priority = PluginPriority.HIGH

    def __init__(self):
        self.call_order = []

    def before_request(self, ctx: RequestContext):
        self.call_order.append('MockPluginV2High')
        return None

    def after_response(self, ctx: RequestContext, response):
        return response

    def on_error(self, ctx: RequestContext, error: Exception) -> bool:
        return False


# ==================== Tests ====================


class TestPluginPriority:
    """Тесты системы приоритетов плагинов."""

    def test_plugin_priority_constants(self):
        """Проверяем что константы приоритетов имеют правильные значения."""
        assert PluginPriority.FIRST == 0
        assert PluginPriority.CACHE == 10
        assert PluginPriority.HIGH == 25
        assert PluginPriority.NORMAL == 50
        assert PluginPriority.LOW == 75
        assert PluginPriority.LAST == 100

    def test_plugin_priority_order(self):
        """Проверяем что FIRST < CACHE < HIGH < NORMAL < LOW < LAST."""
        assert PluginPriority.FIRST < PluginPriority.CACHE
        assert PluginPriority.CACHE < PluginPriority.HIGH
        assert PluginPriority.HIGH < PluginPriority.NORMAL
        assert PluginPriority.NORMAL < PluginPriority.LOW
        assert PluginPriority.LOW < PluginPriority.LAST

    def test_plugin_default_priority(self):
        """Проверяем что плагины без priority получают NORMAL по умолчанию."""
        plugin = MockPluginNoPriority()
        assert getattr(plugin, 'priority', 50) == 50

    def test_plugin_custom_priority(self):
        """Проверяем что кастомный приоритет работает."""
        plugin = MockPluginCustomPriority()
        assert plugin.priority == 15


class TestPluginOrdering:
    """Тесты порядка выполнения плагинов."""

    @patch('http_client.core.http_client.requests.Session.request')
    def test_plugins_execute_in_priority_order(self, mock_request):
        """Проверяем что плагины выполняются в порядке приоритета."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'test'
        mock_response.headers = {}
        mock_request.return_value = mock_response

        # Создаём плагины в обратном порядке (чтобы проверить сортировку)
        plugin_last = MockPluginLast()
        plugin_high = MockPluginHigh()
        plugin_cache = MockPluginCache()
        plugin_first = MockPluginFirst()

        # Создаём shared call_order list
        call_order = []

        # Monkey-patch plugins to use shared list
        plugin_first.call_order = call_order
        plugin_cache.call_order = call_order
        plugin_high.call_order = call_order
        plugin_last.call_order = call_order

        # Создаём клиент с плагинами в неправильном порядке
        client = HTTPClient(
            base_url="https://example.com",
            plugins=[plugin_last, plugin_high, plugin_cache, plugin_first]
        )

        # Выполняем запрос
        client.get("/test")

        # Проверяем порядок выполнения: FIRST -> CACHE -> HIGH -> LAST
        assert call_order == [
            'MockPluginFirst',
            'MockPluginCache',
            'MockPluginHigh',
            'MockPluginLast'
        ]

    @patch('http_client.core.http_client.requests.Session.request')
    def test_add_plugin_maintains_order(self, mock_request):
        """Проверяем что add_plugin сортирует плагины."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'test'
        mock_response.headers = {}
        mock_request.return_value = mock_response

        call_order = []

        plugin_last = MockPluginLast()
        plugin_first = MockPluginFirst()
        plugin_last.call_order = call_order
        plugin_first.call_order = call_order

        # Создаём клиент без плагинов
        client = HTTPClient(base_url="https://example.com")

        # Добавляем в обратном порядке
        client.add_plugin(plugin_last)
        client.add_plugin(plugin_first)

        # Выполняем запрос
        client.get("/test")

        # Проверяем что FIRST выполнился перед LAST
        assert call_order == ['MockPluginFirst', 'MockPluginLast']

    def test_get_plugins_order_method(self):
        """Проверяем метод get_plugins_order()."""
        plugin_last = MockPluginLast()
        plugin_high = MockPluginHigh()
        plugin_first = MockPluginFirst()

        client = HTTPClient(
            base_url="https://example.com",
            plugins=[plugin_last, plugin_high, plugin_first]
        )

        order = client.get_plugins_order()

        # Проверяем формат: список кортежей (имя, приоритет)
        assert isinstance(order, list)
        assert all(isinstance(item, tuple) for item in order)
        assert all(len(item) == 2 for item in order)

        # Проверяем порядок
        assert order == [
            ('MockPluginFirst', 0),
            ('MockPluginHigh', 25),
            ('MockPluginLast', 100)
        ]

    @patch('http_client.core.http_client.requests.Session.request')
    def test_auth_executes_before_cache(self, mock_request):
        """ВАЖНО: AuthPlugin должен выполняться ПЕРЕД CachePlugin."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'test'
        mock_response.headers = {}
        mock_request.return_value = mock_response

        call_order = []

        # Создаём реальные плагины
        auth_plugin = AuthPlugin(auth_type="bearer", token="test-token")
        cache_plugin = CachePlugin()

        # Monkey-patch для отслеживания порядка
        original_auth_before = auth_plugin.before_request
        original_cache_before = cache_plugin.before_request

        def auth_before_wrapper(*args, **kwargs):
            call_order.append('AuthPlugin')
            return original_auth_before(*args, **kwargs)

        def cache_before_wrapper(*args, **kwargs):
            call_order.append('CachePlugin')
            return original_cache_before(*args, **kwargs)

        auth_plugin.before_request = auth_before_wrapper
        cache_plugin.before_request = cache_before_wrapper

        # Создаём клиент с плагинами в обратном порядке
        client = HTTPClient(
            base_url="https://example.com",
            plugins=[cache_plugin, auth_plugin]  # Неправильный порядок!
        )

        # Выполняем запрос
        client.get("/test")

        # Проверяем что AuthPlugin выполнился ПЕРЕД CachePlugin
        assert call_order.index('AuthPlugin') < call_order.index('CachePlugin')

    @patch('http_client.core.http_client.requests.Session.request')
    def test_custom_priority_between_standard(self, mock_request):
        """Проверяем что кастомный приоритет правильно размещается между стандартными."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'test'
        mock_response.headers = {}
        mock_request.return_value = mock_response

        call_order = []

        plugin_cache = MockPluginCache()  # priority = 10
        plugin_custom = MockPluginCustomPriority()  # priority = 15
        plugin_high = MockPluginHigh()  # priority = 25

        plugin_cache.call_order = call_order
        plugin_custom.call_order = call_order
        plugin_high.call_order = call_order

        client = HTTPClient(
            base_url="https://example.com",
            plugins=[plugin_high, plugin_cache, plugin_custom]
        )

        client.get("/test")

        # Порядок: CACHE (10) -> CUSTOM (15) -> HIGH (25)
        assert call_order == [
            'MockPluginCache',
            'MockPluginCustomPriority',
            'MockPluginHigh'
        ]

    @patch('http_client.core.http_client.requests.Session.request')
    def test_stable_sort_preserves_insertion_order(self, mock_request):
        """Проверяем что stable sort сохраняет порядок вставки для одинаковых приоритетов."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'test'
        mock_response.headers = {}
        mock_request.return_value = mock_response

        call_order = []

        # Создаём несколько плагинов с одинаковым приоритетом NORMAL (50)
        plugin1 = MockPluginNormal()
        plugin2 = MockPluginNoPriority()  # Тоже получит NORMAL (50)
        plugin3 = MockPluginNormal()

        plugin1.call_order = call_order
        plugin2.call_order = call_order
        plugin3.call_order = call_order

        # Добавляем в определённом порядке
        client = HTTPClient(base_url="https://example.com")
        client.add_plugin(plugin1)
        client.add_plugin(plugin2)
        client.add_plugin(plugin3)

        client.get("/test")

        # Проверяем что порядок сохранился (stable sort)
        # Все имеют приоритет 50, поэтому должны выполниться в порядке добавления
        assert len(call_order) == 3
        assert call_order[0] == 'MockPluginNormal'
        assert call_order[1] == 'MockPluginNoPriority'
        assert call_order[2] == 'MockPluginNormal'

    def test_real_plugins_have_correct_priorities(self):
        """Проверяем что реальные плагины имеют правильные приоритеты."""
        # AuthPlugin должен иметь FIRST (0)
        auth = AuthPlugin(auth_type="bearer", token="test")
        assert auth.priority == PluginPriority.FIRST

        # CachePlugin должен иметь CACHE (10)
        cache = CachePlugin()
        assert cache.priority == PluginPriority.CACHE

        # RateLimitPlugin должен иметь HIGH (25)
        rate = RateLimitPlugin(max_requests=10)
        assert rate.priority == PluginPriority.HIGH

        # LoggingPlugin должен иметь LAST (100)
        logging_plugin = LoggingPlugin()
        assert logging_plugin.priority == PluginPriority.LAST

        # MonitoringPlugin должен иметь LAST (100)
        monitor = MonitoringPlugin()
        assert monitor.priority == PluginPriority.LAST

    @patch('http_client.core.http_client.requests.Session.request')
    def test_plugin_v2_priority_works(self, mock_request):
        """Проверяем что PluginV2 также поддерживает приоритеты."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'test'
        mock_response.headers = {}
        mock_request.return_value = mock_response

        call_order = []

        plugin_v1 = MockPluginFirst()  # priority = 0
        plugin_v2 = MockPluginV2High()  # priority = 25

        plugin_v1.call_order = call_order
        plugin_v2.call_order = call_order

        client = HTTPClient(
            base_url="https://example.com",
            plugins=[plugin_v2, plugin_v1]  # Обратный порядок
        )

        client.get("/test")

        # V1 plugin (priority=0) должен выполниться перед V2 plugin (priority=25)
        assert call_order.index('MockPluginFirst') < call_order.index('MockPluginV2High')

    def test_backward_compatibility_no_priority_attr(self):
        """Проверяем обратную совместимость с плагинами без атрибута priority."""
        plugin = MockPluginNoPriority()

        # Не должно быть ошибки при вызове getattr
        priority = getattr(plugin, 'priority', 50)
        assert priority == 50

        # Плагин должен работать нормально
        client = HTTPClient(
            base_url="https://example.com",
            plugins=[plugin]
        )

        # Проверяем что плагин в списке
        assert len(client._plugins) == 1
        assert client._plugins[0] is plugin
