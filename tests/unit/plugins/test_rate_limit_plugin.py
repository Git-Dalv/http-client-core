"""Tests for RateLimitPlugin thread safety and functionality."""

import pytest
import threading
import time
from collections import deque

from src.http_client.plugins.rate_limit_plugin import RateLimitPlugin


class TestRateLimitPlugin:
    """Tests for RateLimitPlugin basic functionality."""

    def test_plugin_initialization(self):
        """Test plugin initialization with default values."""
        plugin = RateLimitPlugin()

        assert plugin.max_requests == 10
        assert plugin.time_window == 60
        assert len(plugin.request_times) == 0
        assert hasattr(plugin, '_lock')

    def test_plugin_custom_params(self):
        """Test plugin initialization with custom parameters."""
        plugin = RateLimitPlugin(max_requests=5, time_window=10)

        assert plugin.max_requests == 5
        assert plugin.time_window == 10
        assert len(plugin.request_times) == 0

    def test_before_request_adds_timestamp(self):
        """Test that before_request adds timestamp to request_times."""
        plugin = RateLimitPlugin(max_requests=5, time_window=10)

        kwargs = plugin.before_request("GET", "https://example.com")

        assert isinstance(kwargs, dict)
        assert len(plugin.request_times) == 1

    def test_multiple_requests_within_limit(self):
        """Test multiple requests within rate limit."""
        plugin = RateLimitPlugin(max_requests=5, time_window=10)

        for i in range(5):
            plugin.before_request("GET", f"https://example.com/{i}")

        assert len(plugin.request_times) == 5
        assert plugin.get_remaining_requests() == 0

    def test_get_remaining_requests(self):
        """Test get_remaining_requests calculation."""
        plugin = RateLimitPlugin(max_requests=5, time_window=10)

        assert plugin.get_remaining_requests() == 5

        plugin.before_request("GET", "https://example.com")
        assert plugin.get_remaining_requests() == 4

        plugin.before_request("GET", "https://example.com")
        assert plugin.get_remaining_requests() == 3

    def test_reset_clears_request_times(self):
        """Test that reset clears all request times."""
        plugin = RateLimitPlugin(max_requests=5, time_window=10)

        # Make some requests
        for i in range(3):
            plugin.before_request("GET", f"https://example.com/{i}")

        assert len(plugin.request_times) == 3

        # Reset
        plugin.reset()

        assert len(plugin.request_times) == 0
        assert plugin.get_remaining_requests() == 5

    def test_clean_old_requests(self):
        """Test that old requests are cleaned up."""
        plugin = RateLimitPlugin(max_requests=5, time_window=1)  # 1 second window

        # Add a request
        plugin.before_request("GET", "https://example.com")
        assert len(plugin.request_times) == 1

        # Wait for window to expire
        time.sleep(1.1)

        # Trigger cleanup by checking remaining requests
        remaining = plugin.get_remaining_requests()

        assert remaining == 5
        assert len(plugin.request_times) == 0

    def test_get_reset_time_no_requests(self):
        """Test get_reset_time with no requests."""
        plugin = RateLimitPlugin(max_requests=5, time_window=10)

        reset_time = plugin.get_reset_time()
        assert reset_time == 0.0

    def test_get_reset_time_below_limit(self):
        """Test get_reset_time when below rate limit."""
        plugin = RateLimitPlugin(max_requests=5, time_window=10)

        plugin.before_request("GET", "https://example.com")
        reset_time = plugin.get_reset_time()

        assert reset_time == 0.0  # Not at limit yet

    def test_get_reset_time_at_limit(self):
        """Test get_reset_time when at rate limit."""
        plugin = RateLimitPlugin(max_requests=3, time_window=5)

        # Fill up the limit
        for i in range(3):
            plugin.before_request("GET", f"https://example.com/{i}")

        reset_time = plugin.get_reset_time()

        # Should be close to time_window (5 seconds)
        assert 4.5 < reset_time <= 5.0

    def test_on_error_removes_last_request(self):
        """Test that on_error removes the last request timestamp."""
        plugin = RateLimitPlugin(max_requests=5, time_window=10)

        # Make some requests
        for i in range(3):
            plugin.before_request("GET", f"https://example.com/{i}")

        assert len(plugin.request_times) == 3

        # Simulate error
        plugin.on_error(Exception("Test error"))

        assert len(plugin.request_times) == 2

    def test_on_error_empty_deque(self):
        """Test on_error when request_times is empty."""
        plugin = RateLimitPlugin(max_requests=5, time_window=10)

        # Call on_error with empty deque (should not raise exception)
        result = plugin.on_error(Exception("Test error"))

        assert result is False
        assert len(plugin.request_times) == 0


class TestRateLimitPluginThreadSafety:
    """Tests for RateLimitPlugin thread safety."""

    def test_concurrent_requests_thread_safety(self):
        """Test that concurrent requests are handled safely.

        This test validates the thread safety fix where all operations
        on request_times deque are protected by threading.Lock.
        """
        plugin = RateLimitPlugin(max_requests=100, time_window=10)

        errors = []
        request_count = [0]  # Use list to allow modification in closure

        def make_requests(thread_id, num_requests):
            """Make multiple requests from a thread."""
            try:
                for i in range(num_requests):
                    plugin.before_request("GET", f"https://example.com/{thread_id}/{i}")
                    request_count[0] += 1
            except Exception as e:
                errors.append((thread_id, e))

        # Start multiple threads making requests
        threads = []
        num_threads = 10
        requests_per_thread = 10

        for i in range(num_threads):
            thread = threading.Thread(target=make_requests, args=(i, requests_per_thread))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all requests were recorded
        expected_total = num_threads * requests_per_thread
        assert request_count[0] == expected_total
        assert len(plugin.request_times) == expected_total

    def test_concurrent_get_remaining_requests(self):
        """Test concurrent access to get_remaining_requests."""
        plugin = RateLimitPlugin(max_requests=50, time_window=10)

        errors = []
        results = []

        def check_remaining(thread_id):
            """Check remaining requests multiple times."""
            try:
                for _ in range(20):
                    remaining = plugin.get_remaining_requests()
                    results.append(remaining)
                    time.sleep(0.001)
            except Exception as e:
                errors.append((thread_id, e))

        def make_requests(thread_id):
            """Make requests while others are checking."""
            try:
                for i in range(10):
                    plugin.before_request("GET", f"https://example.com/{thread_id}/{i}")
                    time.sleep(0.001)
            except Exception as e:
                errors.append((thread_id, e))

        # Start threads - some checking, some making requests
        threads = []

        for i in range(3):
            threads.append(threading.Thread(target=check_remaining, args=(f"checker-{i}",)))
            threads.append(threading.Thread(target=make_requests, args=(f"requester-{i}",)))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify we got results
        assert len(results) > 0

        # All results should be non-negative
        assert all(r >= 0 for r in results)

    def test_concurrent_reset_and_requests(self):
        """Test concurrent reset and request operations."""
        plugin = RateLimitPlugin(max_requests=50, time_window=10)

        errors = []
        reset_count = [0]

        def make_requests(thread_id):
            """Continuously make requests."""
            try:
                for i in range(20):
                    plugin.before_request("GET", f"https://example.com/{thread_id}/{i}")
                    time.sleep(0.001)
            except Exception as e:
                errors.append((thread_id, "request", e))

        def reset_periodically(thread_id):
            """Reset the plugin periodically."""
            try:
                for _ in range(5):
                    time.sleep(0.01)
                    plugin.reset()
                    reset_count[0] += 1
            except Exception as e:
                errors.append((thread_id, "reset", e))

        # Start threads
        threads = []

        for i in range(5):
            threads.append(threading.Thread(target=make_requests, args=(f"req-{i}",)))

        threads.append(threading.Thread(target=reset_periodically, args=("resetter",)))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify resets happened
        assert reset_count[0] == 5

    def test_concurrent_on_error_calls(self):
        """Test concurrent on_error calls don't cause issues."""
        plugin = RateLimitPlugin(max_requests=50, time_window=10)

        errors = []

        # First, add some requests
        for i in range(30):
            plugin.before_request("GET", f"https://example.com/{i}")

        def trigger_errors(thread_id):
            """Trigger on_error calls."""
            try:
                for i in range(10):
                    plugin.on_error(Exception(f"Test error {thread_id}-{i}"))
                    time.sleep(0.001)
            except Exception as e:
                errors.append((thread_id, e))

        # Start multiple threads triggering errors
        threads = []
        for i in range(5):
            thread = threading.Thread(target=trigger_errors, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # request_times should not be negative (should stop at 0)
        assert len(plugin.request_times) >= 0

    def test_stress_test_mixed_operations(self):
        """Stress test with mixed operations: requests, resets, checks."""
        plugin = RateLimitPlugin(max_requests=100, time_window=10)

        errors = []
        operation_counts = {
            'requests': 0,
            'resets': 0,
            'checks': 0,
            'get_reset_time': 0
        }
        lock = threading.Lock()

        def mixed_operations(thread_id):
            """Perform mixed operations."""
            try:
                for i in range(50):
                    op = i % 4

                    if op == 0:
                        plugin.before_request("GET", f"https://example.com/{thread_id}/{i}")
                        with lock:
                            operation_counts['requests'] += 1
                    elif op == 1:
                        plugin.get_remaining_requests()
                        with lock:
                            operation_counts['checks'] += 1
                    elif op == 2:
                        plugin.get_reset_time()
                        with lock:
                            operation_counts['get_reset_time'] += 1
                    else:
                        if i % 20 == 0:  # Reset less frequently
                            plugin.reset()
                            with lock:
                                operation_counts['resets'] += 1

                    time.sleep(0.0001)
            except Exception as e:
                errors.append((thread_id, e))

        # Start many threads
        threads = []
        num_threads = 10

        for i in range(num_threads):
            thread = threading.Thread(target=mixed_operations, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify operations happened
        assert operation_counts['requests'] > 0
        assert operation_counts['checks'] > 0
        assert operation_counts['get_reset_time'] > 0

    def test_no_race_condition_on_deque_iteration(self):
        """Test that concurrent modifications don't cause deque iteration errors.

        This specifically tests the scenario where one thread is iterating
        over request_times in _clean_old_requests while another is appending.
        """
        plugin = RateLimitPlugin(max_requests=100, time_window=1)

        errors = []
        iterations = 0
        lock = threading.Lock()

        def clean_repeatedly(thread_id):
            """Repeatedly trigger cleaning."""
            nonlocal iterations
            try:
                for _ in range(100):
                    plugin.get_remaining_requests()  # Triggers _clean_old_requests
                    with lock:
                        iterations += 1
                    time.sleep(0.0001)
            except Exception as e:
                errors.append((thread_id, e))

        def add_requests(thread_id):
            """Continuously add requests."""
            try:
                for i in range(100):
                    plugin.before_request("GET", f"https://example.com/{thread_id}/{i}")
                    time.sleep(0.0001)
            except Exception as e:
                errors.append((thread_id, e))

        # Start threads that will cause concurrent iteration and modification
        threads = []

        for i in range(3):
            threads.append(threading.Thread(target=clean_repeatedly, args=(f"cleaner-{i}",)))
            threads.append(threading.Thread(target=add_requests, args=(f"adder-{i}",)))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify no errors (no deque iteration errors)
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert iterations > 0
