"""
Тесты потокобезопасности плагинов.

Проверяет что плагины корректно работают при многопоточном использовании.
"""

import threading
import time
import pytest

from src.http_client.plugins.rate_limit_plugin import RateLimitPlugin
from src.http_client.plugins.cache_plugin import CachePlugin
from src.http_client.utils.proxy_manager import ProxyPool


class TestRateLimitThreadSafety:
    """Тесты потокобезопасности RateLimitPlugin"""

    def test_rate_limit_concurrent_requests(self):
        """Тест: RateLimitPlugin должен корректно работать при параллельных запросах"""
        plugin = RateLimitPlugin(max_requests=100, time_window=1)
        errors = []
        successful_calls = []

        def make_calls():
            try:
                for _ in range(50):
                    result = plugin.before_request("GET", "http://example.com")
                    successful_calls.append(1)
                    assert result == {}
            except Exception as e:
                errors.append(e)

        # Запускаем 10 потоков по 50 вызовов = 500 вызовов total
        threads = [threading.Thread(target=make_calls) for _ in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Проверки
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(successful_calls) == 500, f"Expected 500 calls, got {len(successful_calls)}"
        assert plugin.get_remaining_requests() >= 0

    def test_rate_limit_concurrent_stats(self):
        """Тест: get_remaining_requests() thread-safe"""
        plugin = RateLimitPlugin(max_requests=50, time_window=10)
        stats = []

        def collect_stats():
            for _ in range(100):
                plugin.before_request("GET", "http://example.com")
                remaining = plugin.get_remaining_requests()
                stats.append(remaining)
                time.sleep(0.001)

        threads = [threading.Thread(target=collect_stats) for _ in range(3)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Все stat вызовы должны вернуть валидные значения (>= 0)
        assert all(s >= 0 for s in stats), "Invalid stat values"
        assert len(stats) == 300


class TestCachePluginThreadSafety:
    """Тесты потокобезопасности CachePlugin"""

    def test_cache_concurrent_writes(self):
        """Тест: CachePlugin должен корректно кэшировать при параллельной записи"""
        plugin = CachePlugin(ttl=10)
        errors = []

        def save_entries():
            try:
                for i in range(50):
                    # Сохраняем разные URL чтобы избежать конфликтов
                    url = f"http://example.com/{threading.current_thread().name}/{i}"
                    import requests
                    response = requests.Response()
                    response.status_code = 200
                    response._content = b"test"

                    plugin.save_to_cache("GET", url, response)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=save_entries, name=f"thread-{i}") for i in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(plugin.cache) > 0, "Cache should have entries"

    def test_cache_concurrent_read_write(self):
        """Тест: CachePlugin thread-safe при одновременном чтении/записи"""
        plugin = CachePlugin(ttl=10)
        errors = []
        hits = []
        misses = []

        def writer():
            try:
                for i in range(30):
                    url = f"http://example.com/item-{i % 10}"
                    import requests
                    response = requests.Response()
                    response.status_code = 200
                    plugin.save_to_cache("GET", url, response)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for i in range(30):
                    url = f"http://example.com/item-{i % 10}"
                    result = plugin.get_from_cache("GET", url)
                    if result:
                        hits.append(1)
                    else:
                        misses.append(1)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        writers = [threading.Thread(target=writer) for _ in range(3)]
        readers = [threading.Thread(target=reader) for _ in range(3)]

        all_threads = writers + readers
        for t in all_threads:
            t.start()

        for t in all_threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(hits) + len(misses) == 90, "All reads should complete"


class TestProxyPoolThreadSafety:
    """Тесты потокобезопасности ProxyPool"""

    def test_proxy_pool_concurrent_add(self):
        """Тест: ProxyPool thread-safe при параллельном добавлении"""
        pool = ProxyPool()
        errors = []
        added_count = []

        def add_proxies():
            try:
                thread_id = threading.current_thread().name
                for i in range(20):
                    host = f"proxy-{thread_id}-{i}.com"
                    pool.add_proxy(host, 8080 + i)
                    added_count.append(1)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_proxies, name=f"t{i}") for i in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(added_count) == 100, f"Expected 100 adds, got {len(added_count)}"
        assert len(pool) == 100, f"Pool should have 100 proxies, got {len(pool)}"

    def test_proxy_pool_concurrent_get(self):
        """Тест: ProxyPool thread-safe при параллельном get_proxy()"""
        pool = ProxyPool(rotation_strategy="round_robin")

        # Добавляем прокси
        for i in range(10):
            pool.add_proxy(f"proxy-{i}.com", 8080)

        errors = []
        retrieved = []

        def get_proxies():
            try:
                for _ in range(50):
                    proxy = pool.get_proxy()
                    if proxy:
                        retrieved.append(proxy)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_proxies) for _ in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(retrieved) == 250, f"Expected 250 retrievals, got {len(retrieved)}"

    def test_proxy_pool_concurrent_record_stats(self):
        """Тест: ProxyPool thread-safe при параллельной записи статистики"""
        pool = ProxyPool()

        # Добавляем прокси
        proxies = []
        for i in range(5):
            proxy = pool.add_proxy(f"proxy-{i}.com", 8080)
            proxies.append(proxy)

        errors = []

        def record_results():
            try:
                for _ in range(100):
                    import random
                    proxy = random.choice(proxies)

                    if random.random() > 0.5:
                        pool.record_success(proxy, 0.1)
                    else:
                        pool.record_failure(proxy)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_results) for _ in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Проверяем что статистика корректна
        stats = pool.get_stats()
        assert stats["total_requests"] == 500, f"Expected 500 requests, got {stats['total_requests']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
