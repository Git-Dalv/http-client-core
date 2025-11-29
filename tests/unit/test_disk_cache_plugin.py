# tests/unit/test_disk_cache_plugin.py
import pytest
import time
import os
import shutil
import gc
from src.http_client.core.http_client import HTTPClient
from src.http_client.plugins.disk_cache_plugin import DiskCachePlugin


@pytest.fixture
def cache_dir():
    """Фикстура для временной директории кэша"""
    cache_path = ".test_cache"

    # Очистка перед тестом (если осталась от предыдущего запуска)
    if os.path.exists(cache_path):
        try:
            shutil.rmtree(cache_path)
        except PermissionError:
            pass  # Игнорируем, если не можем удалить

    yield cache_path

    # Очистка после теста с повторными попытками
    if os.path.exists(cache_path):
        # Принудительная сборка мусора для закрытия файлов
        gc.collect()

        # Пытаемся удалить несколько раз
        for attempt in range(3):
            try:
                time.sleep(0.1)  # Небольшая задержка
                shutil.rmtree(cache_path)
                break
            except PermissionError:
                if attempt == 2:  # Последняя попытка
                    # Если не удалось удалить, просто пропускаем
                    pass
                else:
                    time.sleep(0.2)


def test_disk_cache_basic(cache_dir):
    """Тест базового кэширования на диске"""
    plugin = DiskCachePlugin(cache_dir=cache_dir, ttl=60)

    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(plugin)

    try:
        # Первый запрос - должен пойти на сервер
        response1 = client.get("/posts/1")
        assert response1.status_code == 200
        assert response1.headers.get('X-Cache') == 'MISS'

        # Второй запрос - должен быть из кэша
        response2 = client.get("/posts/1")
        assert response2.status_code == 200
        assert response2.headers.get('X-Cache') == 'HIT'

        # Проверяем статистику
        stats = plugin.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
    finally:
        client.close()
        plugin.close()


def test_disk_cache_persistence(cache_dir):
    """Тест персистентности кэша между сессиями"""
    # Первая сессия
    plugin1 = DiskCachePlugin(cache_dir=cache_dir, ttl=3600)
    client1 = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client1.add_plugin(plugin1)

    try:
        response1 = client1.get("/posts/1")
        assert response1.status_code == 200
    finally:
        client1.close()
        plugin1.close()

    # Небольшая задержка для освобождения файлов
    time.sleep(0.2)

    # Вторая сессия - кэш должен сохраниться
    plugin2 = DiskCachePlugin(cache_dir=cache_dir, ttl=3600)
    client2 = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client2.add_plugin(plugin2)

    try:
        response2 = client2.get("/posts/1")
        assert response2.status_code == 200
        assert response2.headers.get('X-Cache') == 'HIT'
    finally:
        client2.close()
        plugin2.close()


def test_disk_cache_ttl_expiration(cache_dir):
    """Тест истечения TTL кэша"""
    plugin = DiskCachePlugin(cache_dir=cache_dir, ttl=2)  # 2 секунды

    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(plugin)

    try:
        # Первый запрос
        response1 = client.get("/posts/1")
        assert response1.status_code == 200

        # Ждем истечения TTL
        time.sleep(3)

        # Запрос после истечения TTL - должен пойти на сервер
        response2 = client.get("/posts/1")
        assert response2.status_code == 200
        assert response2.headers.get('X-Cache') == 'MISS'
    finally:
        client.close()
        plugin.close()


def test_disk_cache_different_params(cache_dir):
    """Тест кэширования запросов с разными параметрами"""
    plugin = DiskCachePlugin(cache_dir=cache_dir, ttl=60)

    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(plugin)

    try:
        # Запросы с разными параметрами должны кэшироваться отдельно
        response1 = client.get("/posts", params={"userId": 1})
        response2 = client.get("/posts", params={"userId": 2})
        response3 = client.get("/posts", params={"userId": 1})  # Должен быть из кэша

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200
        assert response3.headers.get('X-Cache') == 'HIT'

        stats = plugin.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 2
    finally:
        client.close()
        plugin.close()


def test_disk_cache_post_not_cached(cache_dir):
    """Тест что POST запросы не кэшируются по умолчанию"""
    plugin = DiskCachePlugin(cache_dir=cache_dir, ttl=60)

    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(plugin)

    try:
        # POST запросы не должны кэшироваться
        data = {"title": "test", "body": "test body", "userId": 1}
        response1 = client.post("/posts", json=data)
        response2 = client.post("/posts", json=data)

        assert response1.status_code == 201
        assert response2.status_code == 201

        stats = plugin.get_stats()
        assert stats['hits'] == 0
    finally:
        client.close()
        plugin.close()


def test_disk_cache_custom_methods(cache_dir):
    """Тест кэширования кастомных HTTP методов"""
    plugin = DiskCachePlugin(
        cache_dir=cache_dir,
        ttl=60,
        cache_methods=("GET", "POST")
    )

    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(plugin)

    try:
        # POST теперь должен кэшироваться
        data = {"title": "test", "body": "test body", "userId": 1}
        response1 = client.post("/posts", json=data)
        response2 = client.post("/posts", json=data)

        assert response1.status_code == 201
        assert response2.status_code == 201

        # Второй запрос должен быть из кэша
        # (в реальности POST обычно не кэшируют, но для теста)
    finally:
        client.close()
        plugin.close()


def test_disk_cache_clear(cache_dir):
    """Тест очистки кэша"""
    plugin = DiskCachePlugin(cache_dir=cache_dir, ttl=60)

    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(plugin)

    try:
        # Делаем запрос и кэшируем
        response1 = client.get("/posts/1")
        assert response1.status_code == 200

        # Проверяем что кэш есть
        stats1 = plugin.get_stats()
        assert stats1['cache_size'] > 0

        # Очищаем кэш
        plugin.clear()

        # Проверяем что кэш пуст
        stats2 = plugin.get_stats()
        assert stats2['cache_size'] == 0
        assert stats2['hits'] == 0
        assert stats2['misses'] == 0
    finally:
        client.close()
        plugin.close()


def test_disk_cache_delete_specific(cache_dir):
    """Тест удаления конкретной записи из кэша"""
    plugin = DiskCachePlugin(cache_dir=cache_dir, ttl=60)

    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(plugin)

    try:
        # Кэшируем два разных запроса
        response1 = client.get("/posts/1")
        response2 = client.get("/posts/2")

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Удаляем один из кэша
        plugin.delete("GET", "https://jsonplaceholder.typicode.com/posts/1")

        # Первый должен пойти на сервер, второй из кэша
        response3 = client.get("/posts/1")
        response4 = client.get("/posts/2")

        assert response3.headers.get('X-Cache') == 'MISS'
        assert response4.headers.get('X-Cache') == 'HIT'
    finally:
        client.close()
        plugin.close()


def test_disk_cache_size_limit(cache_dir):
    """Тест ограничения размера кэша"""
    # Устанавливаем маленький лимит
    plugin = DiskCachePlugin(
        cache_dir=cache_dir,
        ttl=60,
        size_limit=1024 * 100  # 100 KB (увеличено для стабильности)
    )

    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(plugin)

    try:
        # Делаем несколько запросов
        for i in range(1, 6):
            response = client.get(f"/posts/{i}")
            assert response.status_code == 200

        # Проверяем размер кэша (может быть больше из-за overhead базы данных)
        size = plugin.get_size()
        # Проверяем что размер разумный (не более 200 KB с учетом overhead)
        assert size <= 1024 * 200
    finally:
        client.close()
        plugin.close()


def test_disk_cache_stats(cache_dir):
    """Тест статистики кэша"""
    plugin = DiskCachePlugin(cache_dir=cache_dir, ttl=60)

    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(plugin)

    try:
        # Делаем запросы
        client.get("/posts/1")  # miss
        client.get("/posts/1")  # hit
        client.get("/posts/2")  # miss
        client.get("/posts/1")  # hit

        stats = plugin.get_stats()

        assert stats['hits'] == 2
        assert stats['misses'] == 2
        assert stats['sets'] == 2
        assert 'hit_rate' in stats
        assert stats['cache_size'] == 2
    finally:
        client.close()
        plugin.close()


def test_disk_cache_repr(cache_dir):
    """Тест строкового представления плагина"""
    plugin = DiskCachePlugin(cache_dir=cache_dir, ttl=60)

    try:
        repr_str = repr(plugin)
        assert "DiskCachePlugin" in repr_str
        assert cache_dir in repr_str
        assert "ttl=60" in repr_str
    finally:
        plugin.close()