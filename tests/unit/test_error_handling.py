# tests/unit/test_error_handling.py

import pytest

from src.http_client.core.exceptions import NotFoundError, TimeoutError, TooManyRetriesError
from src.http_client.core.http_client import HTTPClient


def test_not_found_error():
    """Тест обработки 404 ошибки"""
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")

    with pytest.raises(NotFoundError) as exc_info:
        client.get("/posts/999999")

    assert exc_info.value.status_code == 404


def test_timeout_error():
    """Тест обработки таймаута"""
    client = HTTPClient(base_url="https://httpbin.org", timeout=0.001)

    # Может быть TimeoutError или TooManyRetriesError (из-за retry логики)
    with pytest.raises((TimeoutError, TooManyRetriesError)):
        client.get("/delay/5")


def test_successful_request():
    """Тест успешного запроса"""
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")

    response = client.get("/posts/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1
