"""Тесты retry логики в HTTPClient."""

import pytest
import responses as responses_lib
from src.http_client import HTTPClient
from src.http_client.core.config import HTTPClientConfig, RetryConfig
from src.http_client.core.exceptions import (
    TooManyRetriesError,
    ServerError,
    BadRequestError,
)


@responses_lib.activate
def test_retry_on_500():
    """Retry на 500 ошибку."""
    # 2 fail, 1 success
    responses_lib.add(responses_lib.GET, "https://api.example.com/data", status=500)
    responses_lib.add(responses_lib.GET, "https://api.example.com/data", status=500)
    responses_lib.add(responses_lib.GET, "https://api.example.com/data", json={"ok": True}, status=200)

    config = HTTPClientConfig.create(
        base_url="https://api.example.com",
        max_retries=3
    )
    client = HTTPClient(config=config)

    response = client.get("/data")
    assert response.status_code == 200
    assert len(responses_lib.calls) == 3  # 2 fail + 1 success


@responses_lib.activate
def test_no_retry_on_400():
    """НЕ retry на 400."""
    responses_lib.add(responses_lib.GET, "https://api.example.com/data", status=400)

    client = HTTPClient(base_url="https://api.example.com")

    with pytest.raises(BadRequestError):
        client.get("/data")

    assert len(responses_lib.calls) == 1  # Только 1 попытка


@responses_lib.activate
def test_no_retry_post():
    """НЕ retry POST по умолчанию."""
    responses_lib.add(responses_lib.POST, "https://api.example.com/data", status=500)

    client = HTTPClient(base_url="https://api.example.com")

    with pytest.raises(ServerError):
        client.post("/data", json={"test": "data"})

    assert len(responses_lib.calls) == 1


@responses_lib.activate
def test_too_many_retries():
    """TooManyRetriesError после лимита."""
    # Все fail
    for _ in range(5):
        responses_lib.add(responses_lib.GET, "https://api.example.com/data", status=500)

    config = HTTPClientConfig.create(
        base_url="https://api.example.com",
        max_retries=2
    )
    client = HTTPClient(config=config)

    with pytest.raises(TooManyRetriesError) as exc_info:
        client.get("/data")

    assert exc_info.value.max_retries == 2
    assert len(responses_lib.calls) == 3  # 1 original + 2 retries


def test_immutability():
    """HTTPClient immutable."""
    client = HTTPClient(base_url="https://api.example.com")

    with pytest.raises(RuntimeError, match="immutable"):
        client._config = None
