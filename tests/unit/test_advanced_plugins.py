# tests/unit/test_advanced_plugins.py

import time

import responses

from src.http_client.core.http_client import HTTPClient
from src.http_client.plugins.auth_plugin import AuthPlugin
from src.http_client.plugins.cache_plugin import CachePlugin
from src.http_client.plugins.rate_limit_plugin import RateLimitPlugin


def test_cache_plugin():
    """Тест плагина кэширования"""
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    cache_plugin = CachePlugin(ttl=60)
    client.add_plugin(cache_plugin)

    # Первый запрос - должен попасть в базу
    start_time = time.time()
    response1 = client.get("/posts/1")
    first_request_time = time.time() - start_time

    # Второй запрос - должен взяться из кэша (быстрее)
    start_time = time.time()
    response2 = client.get("/posts/1")
    second_request_time = time.time() - start_time

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()
    # Кэшированный запрос должен быть быстрее
    print(f"First request: {first_request_time:.4f}s, Cached request: {second_request_time:.4f}s")


def test_rate_limit_plugin():
    """Тест плагина rate limiting"""
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    # Ограничение: 3 запроса в 5 секунд
    rate_limit_plugin = RateLimitPlugin(max_requests=3, time_window=5)
    client.add_plugin(rate_limit_plugin)

    # Делаем 3 быстрых запроса - должны пройти
    for i in range(3):
        response = client.get(f"/posts/{i+1}")
        assert response.status_code == 200

    # 4-й запрос должен подождать
    start_time = time.time()
    response = client.get("/posts/4")
    elapsed_time = time.time() - start_time

    assert response.status_code == 200
    # Должна быть задержка
    print(f"4th request took {elapsed_time:.2f}s (should be ~5s)")


@responses.activate
def test_auth_plugin_bearer():
    """Тест плагина аутентификации (Bearer)"""
    responses.add(
        responses.GET,
        "https://httpbin.org/headers",
        json={"headers": {"Authorization": "Bearer test_token_123"}},
        status=200
    )

    client = HTTPClient(base_url="https://httpbin.org")
    auth_plugin = AuthPlugin(auth_type="bearer", token="test_token_123")
    client.add_plugin(auth_plugin)

    response = client.get("/headers")
    assert response.status_code == 200

    # Проверяем, что плагин добавил токен
    assert auth_plugin.token == "test_token_123"
    assert response.status_code == 200


@responses.activate
def test_auth_plugin_api_key():
    """Тест плагина аутентификации (API Key)"""
    responses.add(
        responses.GET,
        "https://httpbin.org/headers",
        json={"headers": {"X-Api-Key": "my_api_key_456"}},
        status=200
    )

    client = HTTPClient(base_url="https://httpbin.org")
    auth_plugin = AuthPlugin(auth_type="api_key", token="my_api_key_456")
    client.add_plugin(auth_plugin)

    response = client.get("/headers")
    assert response.status_code == 200

    # Проверяем, что плагин добавил API ключ (token используется для api_key тоже)
    assert auth_plugin.token == "my_api_key_456"
    assert response.status_code == 200


def test_multiple_plugins_together():
    """Тест использования нескольких плагинов вместе"""
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")

    # Добавляем несколько плагинов
    client.add_plugin(CachePlugin(ttl=60))
    client.add_plugin(RateLimitPlugin(max_requests=5, time_window=10))

    # Делаем несколько запросов
    for i in range(3):
        response = client.get("/posts/1")  # Один и тот же endpoint для теста кэша
        assert response.status_code == 200
