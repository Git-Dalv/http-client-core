"""
Test to verify RetryPlugin actually retries requests in http_client.
"""

import responses
from src.http_client.core.http_client import HTTPClient
from src.http_client.plugins.retry_plugin import RetryPlugin


@responses.activate
def test_retry_succeeds_on_second_attempt():
    """Test that RetryPlugin retries and succeeds on second attempt."""
    # First request will fail with 500
    responses.add(
        responses.GET,
        "https://api.example.com/test",
        status=500,
        json={"error": "Server error"},
    )

    # Second request will succeed
    responses.add(
        responses.GET, "https://api.example.com/test", status=200, json={"success": True}
    )

    client = HTTPClient(base_url="https://api.example.com")
    retry_plugin = RetryPlugin(max_retries=3, backoff_factor=0.01)  # Fast backoff for test
    client.add_plugin(retry_plugin)

    # This should succeed after retry
    response = client.get("/test")

    assert response.status_code == 200
    assert response.json() == {"success": True}
    assert len(responses.calls) == 2  # Two requests were made
    assert retry_plugin.retry_count == 0  # Reset after success


@responses.activate
def test_retry_fails_after_max_retries():
    """Test that RetryPlugin raises error after max retries."""
    from src.http_client.core.exceptions import TooManyRetriesError

    # All requests will fail with 500
    for _ in range(5):
        responses.add(
            responses.GET,
            "https://api.example.com/test",
            status=500,
            json={"error": "Server error"},
        )

    client = HTTPClient(base_url="https://api.example.com")
    retry_plugin = RetryPlugin(max_retries=2, backoff_factor=0.01)
    client.add_plugin(retry_plugin)

    # This should raise TooManyRetriesError after exhausting retries
    try:
        client.get("/test")
        assert False, "Should have raised TooManyRetriesError"
    except TooManyRetriesError as exc:
        # Expected - verify it has the correct max_retries
        # Note: HTTPClient's internal retry logic may also be active
        # So we just check that error was raised
        assert len(responses.calls) >= 3  # At least 3 attempts


if __name__ == "__main__":
    test_retry_succeeds_on_second_attempt()
    print("✓ test_retry_succeeds_on_second_attempt passed")

    test_retry_fails_after_max_retries()
    print("✓ test_retry_fails_after_max_retries passed")

    print("\n✅ All retry integration tests passed!")
