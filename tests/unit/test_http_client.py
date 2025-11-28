# tests/unit/test_http_client.py

from src.http_client.core.http_client import HTTPClient

def test_http_client():
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")

    # Test GET request
    response = client.get("/posts/1")
    assert response.status_code == 200
    assert 'userId' in response.json()

    # Test POST request
    response = client.post("/posts", json={"title": "foo", "body": "bar", "userId": 1})
    assert response.status_code == 201
    assert response.json()["title"] == "foo"
