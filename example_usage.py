# example_usage.py

from src.http_client.core.http_client import HTTPClient
from src.http_client.plugins.logging_plugin import LoggingPlugin
from src.http_client.plugins.cache_plugin import CachePlugin
from src.http_client.plugins.rate_limit_plugin import RateLimitPlugin
from src.http_client.plugins.auth_plugin import AuthPlugin

def main():
    # Создаем клиент
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")

    # Добавляем плагины
    client.add_plugin(LoggingPlugin())
    client.add_plugin(CachePlugin(ttl=300))  # Кэш на 5 минут
    client.add_plugin(RateLimitPlugin(max_requests=10, time_window=60))  # 10 запросов в минуту

    # Делаем запросы
    print("\n=== First request ===")
    response = client.get("/posts/1")
    print(f"Status: {response.status_code}")
    print(f"Title: {response.json()['title']}")

    print("\n=== Second request (should be cached) ===")
    response = client.get("/posts/1")
    print(f"Status: {response.status_code}")

    print("\n=== POST request ===")
    response = client.post("/posts", json={
        "title": "Test Post",
        "body": "This is a test",
        "userId": 1
    })
    print(f"Status: {response.status_code}")
    print(f"Created ID: {response.json()['id']}")

if __name__ == "__main__":
    main()