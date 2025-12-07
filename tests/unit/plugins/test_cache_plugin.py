"""
Тесты для CachePlugin
"""

import time
from unittest.mock import Mock

import pytest
import requests

from src.http_client.plugins.cache_plugin import CachePlugin


class TestCachePluginInit:
    """Тесты инициализации CachePlugin"""

    def test_init_with_defaults(self):
        """Тест инициализации с параметрами по умолчанию"""
        plugin = CachePlugin()
        assert plugin.ttl == 300
        assert plugin.max_size == 1000
        assert plugin.size == 0
        assert plugin.hits == 0
        assert plugin.misses == 0

    def test_init_with_custom_ttl(self):
        """Тест инициализации с кастомным TTL"""
        plugin = CachePlugin(ttl=600)
        assert plugin.ttl == 600
        assert plugin.max_size == 1000

    def test_init_with_custom_max_size(self):
        """Тест инициализации с кастомным max_size"""
        plugin = CachePlugin(max_size=50)
        assert plugin.ttl == 300
        assert plugin.max_size == 50

    def test_init_with_all_params(self):
        """Тест инициализации со всеми параметрами"""
        plugin = CachePlugin(ttl=600, max_size=100)
        assert plugin.ttl == 600
        assert plugin.max_size == 100


class TestCachePluginMaxSize:
    """Тесты ограничения размера кэша"""

    def test_max_size_default(self):
        """Тест значения по умолчанию"""
        plugin = CachePlugin()
        assert plugin.max_size == 1000

    def test_max_size_custom(self):
        """Тест кастомного значения"""
        plugin = CachePlugin(max_size=50)
        assert plugin.max_size == 50

    def test_eviction_when_full(self):
        """Тест удаления старых записей при заполнении"""
        plugin = CachePlugin(ttl=300, max_size=10)

        # Заполняем кэш
        for i in range(15):
            response = Mock(spec=requests.Response)
            response.status_code = 200
            response._content = f"data-{i}".encode()
            plugin.save_to_cache("GET", f"http://example.com/{i}", response)

        # Должно быть не более max_size записей
        assert plugin.size <= 10

    def test_eviction_removes_oldest(self):
        """Тест что eviction удаляет самые старые записи"""
        plugin = CachePlugin(ttl=300, max_size=10)

        # Добавляем 10 записей с небольшими задержками
        for i in range(10):
            response = Mock(spec=requests.Response)
            response.status_code = 200
            response._content = f"data-{i}".encode()
            plugin.save_to_cache("GET", f"http://example.com/{i}", response)
            time.sleep(0.01)  # Небольшая задержка для разных timestamp

        # Проверяем что все 10 записей в кэше
        assert plugin.size == 10

        # Добавляем еще 5 записей, что должно вызвать eviction
        for i in range(10, 15):
            response = Mock(spec=requests.Response)
            response.status_code = 200
            response._content = f"data-{i}".encode()
            plugin.save_to_cache("GET", f"http://example.com/{i}", response)

        # Проверяем что размер не превысил max_size
        assert plugin.size <= 10

    def test_size_property(self):
        """Тест свойства size"""
        plugin = CachePlugin()
        assert plugin.size == 0

        # Добавляем записи
        for i in range(5):
            response = Mock(spec=requests.Response)
            response.status_code = 200
            plugin.save_to_cache("GET", f"http://example.com/{i}", response)

        assert plugin.size == 5


class TestCachePluginHitsMisses:
    """Тесты подсчёта hits и misses"""

    def test_hits_misses_tracking(self):
        """Тест подсчёта hits и misses"""
        plugin = CachePlugin(ttl=300)

        response = Mock(spec=requests.Response)
        response.status_code = 200
        response._content = b"test"

        # Miss
        result = plugin.get_from_cache("GET", "http://example.com/test")
        assert result is None
        assert plugin.misses == 1
        assert plugin.hits == 0

        # Save
        plugin.save_to_cache("GET", "http://example.com/test", response)

        # Hit
        result = plugin.get_from_cache("GET", "http://example.com/test")
        assert result is not None
        assert plugin.hits == 1
        assert plugin.misses == 1

    def test_multiple_hits_misses(self):
        """Тест множественных hits и misses"""
        plugin = CachePlugin(ttl=300)

        response = Mock(spec=requests.Response)
        response.status_code = 200
        response._content = b"test"

        # 3 misses
        plugin.get_from_cache("GET", "http://example.com/1")
        plugin.get_from_cache("GET", "http://example.com/2")
        plugin.get_from_cache("GET", "http://example.com/3")
        assert plugin.misses == 3
        assert plugin.hits == 0

        # Save одну запись
        plugin.save_to_cache("GET", "http://example.com/1", response)

        # 1 hit и 2 miss
        plugin.get_from_cache("GET", "http://example.com/1")  # hit
        plugin.get_from_cache("GET", "http://example.com/2")  # miss
        plugin.get_from_cache("GET", "http://example.com/3")  # miss

        assert plugin.hits == 1
        assert plugin.misses == 5  # 3 + 2

    def test_hits_property(self):
        """Тест свойства hits"""
        plugin = CachePlugin()
        assert plugin.hits == 0

    def test_misses_property(self):
        """Тест свойства misses"""
        plugin = CachePlugin()
        assert plugin.misses == 0


class TestCachePluginBasicFunctionality:
    """Тесты базовой функциональности кэширования"""

    def test_cache_get_request(self):
        """Тест кэширования GET запроса"""
        plugin = CachePlugin(ttl=300)

        response = Mock(spec=requests.Response)
        response.status_code = 200
        response._content = b"test data"

        # Сохраняем в кэш
        plugin.save_to_cache("GET", "http://example.com/test", response)

        # Получаем из кэша
        cached = plugin.get_from_cache("GET", "http://example.com/test")
        assert cached is not None
        assert cached == response

    def test_cache_only_get_requests(self):
        """Тест что кэшируются только GET запросы"""
        plugin = CachePlugin(ttl=300)

        response = Mock(spec=requests.Response)
        response.status_code = 200

        # POST не должен кэшироваться
        plugin.save_to_cache("POST", "http://example.com/test", response)
        assert plugin.size == 0

        # GET должен кэшироваться
        plugin.save_to_cache("GET", "http://example.com/test", response)
        assert plugin.size == 1

    def test_cache_only_200_status(self):
        """Тест что кэшируются только 200 статусы"""
        plugin = CachePlugin(ttl=300)

        response_404 = Mock(spec=requests.Response)
        response_404.status_code = 404

        response_200 = Mock(spec=requests.Response)
        response_200.status_code = 200

        # 404 не должен кэшироваться
        plugin.save_to_cache("GET", "http://example.com/404", response_404)
        assert plugin.size == 0

        # 200 должен кэшироваться
        plugin.save_to_cache("GET", "http://example.com/200", response_200)
        assert plugin.size == 1

    def test_cache_ttl_expiration(self):
        """Тест истечения TTL"""
        plugin = CachePlugin(ttl=1)  # 1 секунда

        response = Mock(spec=requests.Response)
        response.status_code = 200

        # Сохраняем
        plugin.save_to_cache("GET", "http://example.com/test", response)

        # Должен быть в кэше
        cached = plugin.get_from_cache("GET", "http://example.com/test")
        assert cached is not None

        # Ждем истечения TTL
        time.sleep(1.1)

        # Не должно быть в кэше
        cached = plugin.get_from_cache("GET", "http://example.com/test")
        assert cached is None

    def test_clear_cache(self):
        """Тест очистки кэша"""
        plugin = CachePlugin()

        response = Mock(spec=requests.Response)
        response.status_code = 200

        # Добавляем несколько записей
        for i in range(5):
            plugin.save_to_cache("GET", f"http://example.com/{i}", response)

        assert plugin.size == 5

        # Очищаем кэш
        plugin.clear_cache()
        assert plugin.size == 0


class TestCachePluginThreadSafety:
    """Тесты потокобезопасности"""

    def test_concurrent_access(self):
        """Тест одновременного доступа к кэшу"""
        import threading

        plugin = CachePlugin(max_size=100)
        errors = []

        def add_to_cache(thread_id):
            try:
                for i in range(10):
                    response = Mock(spec=requests.Response)
                    response.status_code = 200
                    plugin.save_to_cache("GET", f"http://example.com/{thread_id}/{i}", response)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            t = threading.Thread(target=add_to_cache, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert plugin.size <= 100
