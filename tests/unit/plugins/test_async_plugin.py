"""Тесты для async плагинов."""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

from src.http_client.plugins.async_plugin import AsyncPlugin, SyncPluginAdapter
from src.http_client.plugins.async_cache_plugin import AsyncCachePlugin
from src.http_client.plugins.async_rate_limit_plugin import AsyncRateLimitPlugin
from src.http_client.plugins.async_monitoring_plugin import AsyncMonitoringPlugin
from src.http_client.plugins.plugin import Plugin


# ==================== Тесты AsyncPlugin ====================

class TestAsyncPlugin:
    """Тесты базового AsyncPlugin."""

    @pytest.mark.asyncio
    async def test_async_plugin_before_request(self):
        """Тест before_request возвращает kwargs."""
        plugin = AsyncPlugin()

        result = await plugin.before_request("GET", "https://example.com", foo="bar")

        assert result == {"foo": "bar"}

    @pytest.mark.asyncio
    async def test_async_plugin_after_response(self):
        """Тест after_response возвращает response."""
        plugin = AsyncPlugin()

        response = Mock()
        result = await plugin.after_response(response)

        assert result is response

    @pytest.mark.asyncio
    async def test_async_plugin_on_error(self):
        """Тест on_error не падает."""
        plugin = AsyncPlugin()

        # Не должно упасть
        await plugin.on_error(Exception("test"), url="https://example.com")


# ==================== Тесты SyncPluginAdapter ====================

class DummySyncPlugin(Plugin):
    """Dummy sync плагин для тестов."""

    def __init__(self):
        self.called_methods = []

    def before_request(self, method, url, **kwargs):
        self.called_methods.append('before_request')
        return kwargs

    def after_response(self, response):
        self.called_methods.append('after_response')
        return response

    def on_error(self, error, **kwargs):
        self.called_methods.append('on_error')
        return False


class TestSyncPluginAdapter:
    """Тесты SyncPluginAdapter."""

    @pytest.mark.asyncio
    async def test_adapter_before_request(self):
        """Тест adapter оборачивает sync before_request."""
        sync_plugin = DummySyncPlugin()
        adapter = SyncPluginAdapter(sync_plugin)

        result = await adapter.before_request("GET", "https://example.com", foo="bar")

        assert result == {"foo": "bar"}
        assert 'before_request' in sync_plugin.called_methods

    @pytest.mark.asyncio
    async def test_adapter_after_response(self):
        """Тест adapter оборачивает sync after_response."""
        sync_plugin = DummySyncPlugin()
        adapter = SyncPluginAdapter(sync_plugin)

        response = Mock()
        result = await adapter.after_response(response)

        assert result is response
        assert 'after_response' in sync_plugin.called_methods

    @pytest.mark.asyncio
    async def test_adapter_on_error(self):
        """Тест adapter оборачивает sync on_error."""
        sync_plugin = DummySyncPlugin()
        adapter = SyncPluginAdapter(sync_plugin)

        await adapter.on_error(Exception("test"), url="https://example.com")

        assert 'on_error' in sync_plugin.called_methods

    @pytest.mark.asyncio
    async def test_adapter_runs_in_executor(self):
        """Тест что adapter не блокирует event loop."""
        sync_plugin = DummySyncPlugin()
        adapter = SyncPluginAdapter(sync_plugin)

        # Запускаем два adapter параллельно
        start = time.time()
        await asyncio.gather(
            adapter.before_request("GET", "https://example.com"),
            adapter.before_request("GET", "https://example.com"),
        )
        elapsed = time.time() - start

        # Должны выполниться быстро (не последовательно)
        assert elapsed < 1.0


# ==================== Тесты AsyncCachePlugin ====================

class TestAsyncCachePlugin:
    """Тесты AsyncCachePlugin."""

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Тест cache miss."""
        cache = AsyncCachePlugin(ttl=10)

        # Первый запрос - miss
        kwargs = await cache.before_request("GET", "https://api.example.com/data")

        assert "__cached_response__" not in kwargs
        assert "__cache_key__" in kwargs

    @pytest.mark.asyncio
    async def test_cache_stores_successful_response(self):
        """Тест что успешный ответ сохраняется в кэш."""
        cache = AsyncCachePlugin(ttl=10)

        # Before request
        kwargs = await cache.before_request("GET", "https://api.example.com/data")
        cache_key = kwargs["__cache_key__"]

        # Создаем mock response
        response = Mock()
        response.status_code = 200
        response.url = "https://api.example.com/data"
        response.request = Mock()
        response.request.__cache_key__ = cache_key

        # After response - должен сохранить
        await cache.after_response(response)

        # Проверяем что сохранилось
        stats = await cache.get_stats()
        assert stats["size"] == 1

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Тест cache hit."""
        cache = AsyncCachePlugin(ttl=10)

        # Первый запрос
        kwargs1 = await cache.before_request("GET", "https://api.example.com/data")
        cache_key = kwargs1["__cache_key__"]

        # Сохраняем response
        response = Mock()
        response.status_code = 200
        response.url = "https://api.example.com/data"
        response.request = Mock()
        response.request.__cache_key__ = cache_key

        await cache.after_response(response)

        # Второй запрос - должен быть hit
        kwargs2 = await cache.before_request("GET", "https://api.example.com/data")

        assert "__cached_response__" in kwargs2
        assert kwargs2["__cached_response__"] is response

    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Тест получения статистики."""
        cache = AsyncCachePlugin(ttl=10)

        stats = await cache.get_stats()

        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 0


# ==================== Тесты AsyncRateLimitPlugin ====================

class TestAsyncRateLimitPlugin:
    """Тесты AsyncRateLimitPlugin."""

    @pytest.mark.asyncio
    async def test_rate_limit_allows_requests_under_limit(self):
        """Тест что запросы проходят если под лимитом."""
        limiter = AsyncRateLimitPlugin(max_requests=5, time_window=60)

        # 5 запросов должны пройти быстро
        start = time.time()
        for i in range(5):
            await limiter.before_request("GET", f"https://example.com/{i}")
        elapsed = time.time() - start

        assert elapsed < 1.0  # Все должны пройти быстро

    @pytest.mark.asyncio
    async def test_rate_limit_throttles_excess_requests(self):
        """Тест что избыточные запросы throttled."""
        limiter = AsyncRateLimitPlugin(max_requests=2, time_window=1)

        # Первые 2 запроса быстро
        await limiter.before_request("GET", "https://example.com/1")
        await limiter.before_request("GET", "https://example.com/2")

        # 3-й запрос должен подождать ~1 секунду
        start = time.time()
        await limiter.before_request("GET", "https://example.com/3")
        elapsed = time.time() - start

        assert 0.8 <= elapsed <= 1.5  # Должен был подождать ~1 секунду

    @pytest.mark.asyncio
    async def test_rate_limit_get_remaining_requests(self):
        """Тест получения оставшихся запросов."""
        limiter = AsyncRateLimitPlugin(max_requests=5, time_window=60)

        remaining = await limiter.get_remaining_requests()
        assert remaining == 5

        await limiter.before_request("GET", "https://example.com")

        remaining = await limiter.get_remaining_requests()
        assert remaining == 4


# ==================== Тесты AsyncMonitoringPlugin ====================

class TestAsyncMonitoringPlugin:
    """Тесты AsyncMonitoringPlugin."""

    @pytest.mark.asyncio
    async def test_monitoring_tracks_requests(self):
        """Тест что мониторинг отслеживает запросы."""
        monitor = AsyncMonitoringPlugin()

        # Before request
        kwargs = await monitor.before_request("GET", "https://api.example.com/data")

        # Создаем mock response
        response = Mock()
        response.status_code = 200
        response.url = "https://api.example.com/data"
        response.request = Mock()
        response.request._start_time = kwargs["_start_time"]
        response.request._method = "GET"
        response.request._url = "https://api.example.com/data"

        # After response
        await monitor.after_response(response)

        # Проверяем метрики
        metrics = await monitor.get_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["successful_requests"] == 1
        assert metrics["method_stats"]["GET"] == 1
        assert metrics["status_code_stats"][200] == 1

    @pytest.mark.asyncio
    async def test_monitoring_tracks_errors(self):
        """Тест что мониторинг отслеживает ошибки."""
        monitor = AsyncMonitoringPlugin()

        await monitor.on_error(Exception("test error"), url="https://example.com")

        metrics = await monitor.get_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["failed_requests"] == 1

    @pytest.mark.asyncio
    async def test_monitoring_calculates_metrics(self):
        """Тест вычисления метрик."""
        monitor = AsyncMonitoringPlugin()

        # Успешный запрос
        kwargs = await monitor.before_request("GET", "https://api.example.com/data")
        response = Mock()
        response.status_code = 200
        response.url = "https://api.example.com/data"
        response.request = Mock()
        response.request._start_time = kwargs["_start_time"]
        response.request._method = "GET"
        response.request._url = "https://api.example.com/data"
        await monitor.after_response(response)

        # Неудачный запрос
        await monitor.on_error(Exception("test"), url="https://example.com")

        metrics = await monitor.get_metrics()
        assert metrics["total_requests"] == 2
        assert metrics["successful_requests"] == 1
        assert metrics["failed_requests"] == 1
        assert metrics["success_rate"] == 50.0
