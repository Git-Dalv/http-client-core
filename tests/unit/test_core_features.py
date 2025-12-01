# tests/unit/test_core_features.py

import pytest

from src.http_client.core.http_client import HTTPClient
from src.http_client.plugins.logging_plugin import LoggingPlugin


def test_connection_pooling():
    """Тест настройки connection pooling"""
    client = HTTPClient(
        base_url="https://jsonplaceholder.typicode.com", pool_connections=5, pool_maxsize=20
    )

    # Проверяем, что адаптеры установлены
    assert "https://" in client.session.adapters
    assert "http://" in client.session.adapters

    # Делаем несколько запросов для проверки переиспользования соединений
    for i in range(5):
        response = client.get(f"/posts/{i+1}")
        assert response.status_code == 200

    client.close()


def test_cookie_management():
    """Тест управления куками"""
    client = HTTPClient(base_url="https://httpbin.org")

    # Устанавливаем куку (supercookie - для всех доменов)
    client.set_cookie("test_cookie", "test_value")

    # Проверяем, что кука установлена
    cookies = client.get_cookies()
    assert "test_cookie" in cookies
    assert cookies["test_cookie"] == "test_value"

    # Делаем запрос и проверяем, что кука отправлена
    response = client.get("/cookies")
    assert response.status_code == 200
    response_cookies = response.json().get("cookies", {})
    assert "test_cookie" in response_cookies

    # Устанавливаем куку с конкретным доменом
    client.set_cookie("domain_cookie", "domain_value", domain="httpbin.org")
    cookies = client.get_cookies()
    assert "domain_cookie" in cookies

    # Удаляем куку
    client.remove_cookie("test_cookie")
    cookies = client.get_cookies()
    assert "test_cookie" not in cookies

    # Очищаем все куки
    client.set_cookie("cookie1", "value1")
    client.set_cookie("cookie2", "value2")
    assert len(client.get_cookies()) >= 2

    client.clear_cookies()
    assert len(client.get_cookies()) == 0

    client.close()


def test_cookie_with_domain():
    """Тест кук с конкретным доменом"""
    client = HTTPClient(base_url="https://httpbin.org")

    # Устанавливаем куку для конкретного домена
    client.set_cookie("site_cookie", "site_value", domain="httpbin.org", path="/")

    cookies = client.get_cookies()
    assert "site_cookie" in cookies

    # Делаем запрос
    response = client.get("/cookies")
    assert response.status_code == 200

    # Удаляем куку по домену
    client.remove_cookie("site_cookie", domain="httpbin.org")
    cookies = client.get_cookies()
    assert "site_cookie" not in cookies

    client.close()


def test_proxy_support():
    """Тест поддержки прокси"""
    # Примечание: этот тест не использует реальный прокси
    # Проверяем только установку и получение прокси

    proxies = {"http": "http://proxy.example.com:8080", "https": "https://proxy.example.com:8080"}

    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com", proxies=proxies)

    # Проверяем, что прокси установлены
    assert client.get_proxies() == proxies

    # Изменяем прокси
    new_proxies = {"http": "http://newproxy.example.com:8080"}
    client.set_proxies(new_proxies)
    assert client.get_proxies() == new_proxies

    # Удаляем прокси
    client.clear_proxies()
    assert client.get_proxies() is None

    client.close()


def test_context_manager():
    """Тест контекстного менеджера"""
    # Используем with для автоматического закрытия
    with HTTPClient(base_url="https://jsonplaceholder.typicode.com") as client:
        response = client.get("/posts/1")
        assert response.status_code == 200

        # Проверяем, что клиент работает внутри контекста
        assert client.session is not None

    # После выхода из контекста сессия закрыта
    # (прямая проверка закрытия сессии сложна, но важно, что не возникает ошибок)


def test_immutability():
    """Тест защиты от изменения конфигурации"""
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")

    # Попытка изменить публичный атрибут должна вызвать ошибку
    with pytest.raises(RuntimeError) as exc_info:
        client.timeout = 5

    assert "immutable" in str(exc_info.value).lower()

    # Но внутренние атрибуты (с _) можно изменять через специальные методы
    # Это нормальное поведение

    client.close()


def test_header_management():
    """Тест управления заголовками"""
    client = HTTPClient(
        base_url="https://httpbin.org", headers={"X-Custom-Header": "initial_value"}
    )

    # Проверяем начальный заголовок
    headers = client.get_headers()
    assert "X-Custom-Header" in headers
    assert headers["X-Custom-Header"] == "initial_value"

    # Устанавливаем новый заголовок
    client.set_header("X-Another-Header", "another_value")

    # Делаем запрос и проверяем заголовки
    response = client.get("/headers")
    assert response.status_code == 200
    response_headers = response.json()["headers"]
    assert "X-Custom-Header" in response_headers
    assert "X-Another-Header" in response_headers

    # Удаляем заголовок
    client.remove_header("X-Custom-Header")
    headers = client.get_headers()
    assert "X-Custom-Header" not in headers

    client.close()


def test_absolute_url_handling():
    """Тест обработки абсолютных URL"""
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")

    # Запрос с относительным URL
    response1 = client.get("/posts/1")
    assert response1.status_code == 200

    # Запрос с абсолютным URL (должен игнорировать base_url)
    response2 = client.get("https://httpbin.org/get")
    assert response2.status_code == 200

    client.close()


def test_ssl_verification():
    """Тест настройки проверки SSL"""
    # С проверкой SSL (по умолчанию)
    client1 = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    response1 = client1.get("/posts/1")
    assert response1.status_code == 200
    client1.close()

    # Без проверки SSL
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        client2 = HTTPClient(base_url="https://jsonplaceholder.typicode.com", verify_ssl=False)
        response2 = client2.get("/posts/1")
        assert response2.status_code == 200
        client2.close()


def test_timeout_override():
    """Тест переопределения таймаута в конкретном запросе"""
    client = HTTPClient(base_url="https://httpbin.org", timeout=10)

    # Запрос с дефолтным таймаутом
    response1 = client.get("/delay/1")
    assert response1.status_code == 200

    # Запрос с переопределенным таймаутом
    response2 = client.get("/delay/1", timeout=5)
    assert response2.status_code == 200

    client.close()


def test_multiple_plugins_with_new_features():
    """Тест работы плагинов с новыми возможностями"""
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com", pool_connections=5)

    # Добавляем плагин
    client.add_plugin(LoggingPlugin())

    # Устанавливаем куку (supercookie)
    client.set_cookie("session_id", "abc123")

    # Делаем запрос
    response = client.get("/posts/1")
    assert response.status_code == 200

    # Проверяем, что кука сохранилась
    cookies = client.get_cookies()
    assert "session_id" in cookies
    assert cookies["session_id"] == "abc123"

    client.close()


def test_plugin_management():
    """Тест управления плагинами"""
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")

    # Добавляем плагин
    plugin = LoggingPlugin()
    client.add_plugin(plugin)
    assert len(client._plugins) == 1

    # Удаляем плагин
    client.remove_plugin(plugin)
    assert len(client._plugins) == 0

    # Добавляем несколько плагинов
    client.add_plugin(LoggingPlugin())
    client.add_plugin(LoggingPlugin())
    assert len(client._plugins) == 2

    # Очищаем все плагины
    client.clear_plugins()
    assert len(client._plugins) == 0

    client.close()


def test_session_persistence():
    """Тест сохранения состояния между запросами"""
    client = HTTPClient(base_url="https://httpbin.org")

    # Устанавливаем куку
    client.set_cookie("persistent_cookie", "persistent_value")

    # Делаем первый запрос
    response1 = client.get("/cookies")
    assert response1.status_code == 200
    cookies1 = response1.json().get("cookies", {})
    assert "persistent_cookie" in cookies1

    # Делаем второй запрос - кука должна сохраниться
    response2 = client.get("/cookies")
    assert response2.status_code == 200
    cookies2 = response2.json().get("cookies", {})
    assert "persistent_cookie" in cookies2

    client.close()


def test_max_redirects():
    """Тест настройки максимального количества редиректов"""
    client = HTTPClient(base_url="https://httpbin.org", max_redirects=5)
    # Тест редиректа
    response = client.get("/redirect/3")

    assert response.status_code == 200

    client.close()


def test_base_url_property():
    """Тест свойства base_url"""
    base_url = "https://jsonplaceholder.typicode.com"
    client = HTTPClient(base_url=base_url)

    # Проверяем, что base_url доступен через свойство
    assert client.base_url == base_url

    # Проверяем, что нельзя изменить
    with pytest.raises(RuntimeError):
        client.base_url = "https://example.com"

    client.close()


def test_timeout_property():
    """Тест свойства timeout"""
    timeout = 15
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com", timeout=timeout)

    # Проверяем, что timeout доступен через свойство
    assert client.timeout == timeout

    client.close()
