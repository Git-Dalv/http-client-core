# tests/unit/test_rate_limit_debug.py


from src.http_client.plugins.rate_limit_plugin import RateLimitPlugin


def test_rate_limit_plugin_creation():
    """Тест создания плагина"""
    plugin = RateLimitPlugin(max_requests=5, time_window=10)

    assert plugin.max_requests == 5
    assert plugin.time_window == 10
    assert len(plugin.request_times) == 0
    print("Plugin created successfully!")


def test_rate_limit_plugin_methods():
    """Тест методов плагина"""
    plugin = RateLimitPlugin(max_requests=3, time_window=5)

    # Тест before_request
    kwargs = plugin.before_request("GET", "https://example.com", params={"test": "value"})
    assert isinstance(kwargs, dict)
    assert len(plugin.request_times) == 1

    # Тест get_remaining_requests
    remaining = plugin.get_remaining_requests()
    assert remaining == 2

    # Тест reset
    plugin.reset()
    assert len(plugin.request_times) == 0

    print("All methods work correctly!")


if __name__ == "__main__":
    test_rate_limit_plugin_creation()
    test_rate_limit_plugin_methods()
    print("\nAll tests passed!")
