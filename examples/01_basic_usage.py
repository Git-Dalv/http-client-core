"""
Basic HTTP Client Usage Examples

Demonstrates simple GET, POST, PUT, DELETE requests.
"""

from src.http_client import HTTPClient


def basic_get_request():
    """Simple GET request."""
    print("\n=== Basic GET Request ===")
    
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    response = client.get("/posts/1")
    
    print(f"Status: {response.status_code}")
    print(f"Data: {response.json()}")


def post_with_json():
    """POST request with JSON body."""
    print("\n=== POST with JSON ===")
    
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    
    data = {
        "title": "My Post",
        "body": "This is the content",
        "userId": 1
    }
    
    response = client.post("/posts", json=data)
    print(f"Status: {response.status_code}")
    print(f"Created: {response.json()}")


def put_request():
    """PUT request to update resource."""
    print("\n=== PUT Request ===")
    
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    
    data = {
        "id": 1,
        "title": "Updated Title",
        "body": "Updated content",
        "userId": 1
    }
    
    response = client.put("/posts/1", json=data)
    print(f"Status: {response.status_code}")
    print(f"Updated: {response.json()}")


def delete_request():
    """DELETE request."""
    print("\n=== DELETE Request ===")
    
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    response = client.delete("/posts/1")
    
    print(f"Status: {response.status_code}")
    print("Resource deleted")


def with_query_params():
    """GET request with query parameters."""
    print("\n=== GET with Query Params ===")
    
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    response = client.get("/posts", params={"userId": 1})
    
    posts = response.json()
    print(f"Found {len(posts)} posts for user 1")


def with_custom_headers():
    """Request with custom headers."""
    print("\n=== Custom Headers ===")
    
    client = HTTPClient(
        base_url="https://httpbin.org",
        headers={"X-Custom-Header": "MyValue"}
    )
    
    response = client.get("/headers")
    print(f"Headers sent: {response.json()['headers']}")


def with_timeout():
    """Request with custom timeout."""
    print("\n=== Custom Timeout ===")
    
    client = HTTPClient(
        base_url="https://httpbin.org",
        timeout=5  # 5 seconds
    )
    
    response = client.get("/delay/2")  # Server delays 2 seconds
    print(f"Status: {response.status_code}")
    print("Request completed within timeout")


def context_manager():
    """Using client as context manager."""
    print("\n=== Context Manager ===")
    
    with HTTPClient(base_url="https://jsonplaceholder.typicode.com") as client:
        response = client.get("/posts/1")
        print(f"Status: {response.status_code}")
        print(f"Data: {response.json()}")
    # Session automatically closed


if __name__ == "__main__":
    print("=" * 50)
    print("HTTP Client - Basic Usage Examples")
    print("=" * 50)
    
    try:
        basic_get_request()
        post_with_json()
        put_request()
        delete_request()
        with_query_params()
        with_custom_headers()
        with_timeout()
        context_manager()
        
        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
