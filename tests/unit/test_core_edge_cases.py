# tests/unit/test_core_edge_cases.py
import pytest
import responses
from src.http_client.core.exceptions import NotFoundError, TimeoutError, TooManyRetriesError
from src.http_client.core.http_client import HTTPClient


def test_404_error_handling():
    """Тест обработки 404 ошибки"""
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")

    with pytest.raises(NotFoundError) as exc_info:
        client.get("/nonexistent-endpoint-12345")

    assert exc_info.value.status_code == 404
    client.close()


def test_timeout_handling():
    """Тест обработки таймаута"""
    client = HTTPClient(base_url="https://httpbin.org", timeout=1)

    # Может быть TimeoutError или TooManyRetriesError (из-за retry логики)
    with pytest.raises((TimeoutError, TooManyRetriesError)):
        # Запрашиваем задержку больше таймаута
        client.get("/delay/5")

    client.close()


def test_empty_cookies():
    """Тест работы с пустыми куками"""
    client = HTTPClient(base_url="https://httpbin.org")

    # Изначально куки должны быть пустыми
    cookies = client.get_cookies()
    assert isinstance(cookies, dict)

    client.close()


def test_multiple_cookie_operations():
    """Тест множественных операций с куками"""
    client = HTTPClient(base_url="https://httpbin.org")

    # Устанавливаем несколько кук
    client.set_cookie("cookie1", "value1")
    client.set_cookie("cookie2", "value2")
    client.set_cookie("cookie3", "value3")

    cookies = client.get_cookies()
    assert len(cookies) >= 3
    assert cookies["cookie1"] == "value1"
    assert cookies["cookie2"] == "value2"
    assert cookies["cookie3"] == "value3"

    # Удаляем одну куку
    client.remove_cookie("cookie2")
    cookies = client.get_cookies()
    assert "cookie2" not in cookies
    assert "cookie1" in cookies
    assert "cookie3" in cookies

    client.close()


def test_url_building():
    """Тест построения URL"""
    client = HTTPClient(base_url="https://api.example.com/v1")

    # Тестируем приватный метод через публичный интерфейс
    url1 = client._build_url("/users")
    assert url1 == "https://api.example.com/v1/users"

    url2 = client._build_url("users")  # без слеша
    assert url2 == "https://api.example.com/v1/users"

    url3 = client._build_url("https://other-api.com/endpoint")
    assert url3 == "https://other-api.com/endpoint"

    client.close()


def test_session_property():
    """Тест доступа к сессии"""
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")

    # Проверяем, что можем получить доступ к сессии
    session = client.session
    assert session is not None
    assert hasattr(session, "get")
    assert hasattr(session, "post")

    client.close()


def test_close_multiple_times():
    """Тест множественного вызова close()"""
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")

    # Закрываем несколько раз - не должно быть ошибок
    client.close()
    client.close()
    client.close()


def test_context_manager_with_error():
    """Тест контекстного менеджера при ошибке"""
    try:
        with HTTPClient(base_url="https://jsonplaceholder.typicode.com") as client:
            response = client.get("/posts/1")
            assert response.status_code == 200
            # Генерируем ошибку
            raise ValueError("Test error")
    except ValueError:
        # Ошибка должна быть поймана, но сессия должна закрыться
        pass


@responses.activate
def test_http_methods():
    """Тест всех HTTP методов"""
    # Mock all HTTP methods endpoints
    responses.add(
        responses.GET,
        "https://httpbin.org/get",
        json={"args": {}, "headers": {}, "origin": "127.0.0.1", "url": "https://httpbin.org/get"},
        status=200
    )
    responses.add(
        responses.POST,
        "https://httpbin.org/post",
        json={"args": {}, "data": '{"key": "value"}', "json": {"key": "value"}, "url": "https://httpbin.org/post"},
        status=200
    )
    responses.add(
        responses.PUT,
        "https://httpbin.org/put",
        json={"args": {}, "data": '{"key": "value"}', "json": {"key": "value"}, "url": "https://httpbin.org/put"},
        status=200
    )
    responses.add(
        responses.DELETE,
        "https://httpbin.org/delete",
        json={"args": {}, "data": "", "url": "https://httpbin.org/delete"},
        status=200
    )
    responses.add(
        responses.PATCH,
        "https://httpbin.org/patch",
        json={"args": {}, "data": '{"key": "value"}', "json": {"key": "value"}, "url": "https://httpbin.org/patch"},
        status=200
    )
    responses.add(
        responses.HEAD,
        "https://httpbin.org/get",
        status=200
    )
    responses.add(
        responses.OPTIONS,
        "https://httpbin.org/get",
        status=200
    )

    client = HTTPClient(base_url="https://httpbin.org")

    # GET
    response = client.get("/get")
    assert response.status_code == 200

    # POST
    response = client.post("/post", json={"key": "value"})
    assert response.status_code == 200

    # PUT
    response = client.put("/put", json={"key": "value"})
    assert response.status_code == 200

    # DELETE
    response = client.delete("/delete")
    assert response.status_code == 200

    # PATCH
    response = client.patch("/patch", json={"key": "value"})
    assert response.status_code == 200

    # HEAD
    response = client.head("/get")
    assert response.status_code == 200

    # OPTIONS
    response = client.options("/get")
    assert response.status_code == 200

    client.close()
