# tests/unit/test_plugins.py

from src.http_client.core.http_client import HTTPClient
from src.http_client.plugins.logging_plugin import LoggingPlugin
from src.http_client.plugins.retry_plugin import RetryPlugin


def test_logging_plugin():
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")

    # Добавляем плагин логирования
    logging_plugin = LoggingPlugin()
    client.add_plugin(logging_plugin)

    # Выполняем запрос
    response = client.get("/posts/1")
    assert response.status_code == 200


def test_retry_plugin():
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")

    # Добавляем плагин retry
    retry_plugin = RetryPlugin(max_retries=2, backoff_factor=0.1)
    client.add_plugin(retry_plugin)

    # Выполняем запрос
    response = client.get("/posts/1")
    assert response.status_code == 200


def test_multiple_plugins():
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")

    # Добавляем несколько плагинов
    client.add_plugin(LoggingPlugin())
    client.add_plugin(RetryPlugin(max_retries=2))

    # Выполняем запрос
    response = client.get("/posts/1")
    assert response.status_code == 200
