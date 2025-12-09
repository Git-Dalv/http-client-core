"""Tests for ProxyPool thread-safety and concurrent operations."""

import pytest
import threading
import time
from unittest.mock import patch, MagicMock
from src.http_client.utils.proxy_manager import ProxyPool, ProxyInfo


def test_concurrent_add_proxy_without_check():
    """Test concurrent adding of different proxies without HTTP checks."""
    pool = ProxyPool(check_on_add=False)
    errors = []

    def add_proxy_worker(index):
        try:
            pool.add_proxy(f"proxy{index}.com", 8080 + index)
        except Exception as e:
            errors.append(e)

    # Create 10 threads adding different proxies
    threads = []
    for i in range(10):
        t = threading.Thread(target=add_proxy_worker, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join()

    # Verify no errors and all proxies added
    assert len(errors) == 0
    assert len(pool) == 10


def test_concurrent_add_duplicate_proxies():
    """Test concurrent adding of same proxy - only one should succeed."""
    pool = ProxyPool(check_on_add=False)
    success_count = []
    errors = []

    def add_same_proxy():
        try:
            pool.add_proxy("proxy.com", 8080)
            success_count.append(1)
        except ValueError as e:
            # Expected: duplicate error
            errors.append(e)

    # Create 10 threads trying to add the same proxy
    threads = []
    for i in range(10):
        t = threading.Thread(target=add_same_proxy)
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join()

    # Only one should succeed, others should get ValueError
    assert len(success_count) == 1, f"Expected 1 success, got {len(success_count)}"
    assert len(errors) == 9, f"Expected 9 errors, got {len(errors)}"
    assert len(pool) == 1
    assert all("already exists" in str(e) for e in errors)


@patch('src.http_client.utils.proxy_manager.requests.get')
def test_concurrent_add_proxy_with_check_no_deadlock(mock_get):
    """
    Test concurrent adding with check_on_add=True - should NOT deadlock.

    This is the key test for the deadlock fix:
    - Multiple threads add proxies with check_on_add=True
    - Each add_proxy() calls _check_proxy() which makes HTTP request
    - HTTP request should NOT block other threads (lock must be released during HTTP call)
    """
    # Mock HTTP response to simulate slow network (simulates real-world delay)
    mock_response = MagicMock()
    mock_response.status_code = 200

    def slow_http_get(*args, **kwargs):
        """Simulate slow HTTP request (0.1s)"""
        time.sleep(0.1)  # Simulate network delay
        return mock_response

    mock_get.side_effect = slow_http_get

    # Create pool with check_on_add=True (this was causing deadlock before fix)
    pool = ProxyPool(check_on_add=True, check_timeout=1.0)

    start_time = time.time()
    errors = []
    success_count = []

    def add_proxy_with_check(index):
        try:
            pool.add_proxy(f"proxy{index}.com", 8080 + index)
            success_count.append(1)
        except Exception as e:
            errors.append(e)

    # Create 5 threads adding different proxies
    # If deadlock exists, these threads will block each other
    # Total time should be ~0.5s (5 threads * 0.1s), not 0.5s sequentially
    threads = []
    for i in range(5):
        t = threading.Thread(target=add_proxy_with_check, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join()

    elapsed = time.time() - start_time

    # Verify no errors
    assert len(errors) == 0, f"Unexpected errors: {errors}"
    assert len(success_count) == 5
    assert len(pool) == 5

    # KEY ASSERTION: If there was a deadlock, execution would be sequential (5 * 0.1s = 0.5s+)
    # With fix, threads should run concurrently, so total time should be much less
    # Allow some overhead, but it should be significantly less than sequential
    assert elapsed < 0.4, (
        f"Took {elapsed:.2f}s - possible deadlock! "
        f"Expected concurrent execution (~0.1-0.2s), got {elapsed:.2f}s"
    )

    # Verify HTTP check was called for each proxy
    assert mock_get.call_count == 5


@patch('src.http_client.utils.proxy_manager.requests.get')
def test_concurrent_add_with_check_duplicates(mock_get):
    """Test concurrent adding of same proxy with check_on_add=True."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    pool = ProxyPool(check_on_add=True, check_timeout=1.0)
    success_count = []
    errors = []

    def add_same_proxy_with_check():
        try:
            pool.add_proxy("proxy.com", 8080)
            success_count.append(1)
        except ValueError as e:
            errors.append(e)

    # Create 5 threads trying to add the same proxy
    threads = []
    for i in range(5):
        t = threading.Thread(target=add_same_proxy_with_check)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Only one should succeed (double-checked locking prevents duplicates)
    assert len(success_count) == 1
    assert len(errors) == 4
    assert len(pool) == 1


@patch('src.http_client.utils.proxy_manager.requests.get')
def test_add_proxy_with_failed_check(mock_get):
    """Test adding proxy that fails HTTP check."""
    # Simulate failing proxy
    mock_get.side_effect = Exception("Connection refused")

    pool = ProxyPool(check_on_add=True, check_timeout=1.0)

    with pytest.raises(ValueError) as exc_info:
        pool.add_proxy("bad-proxy.com", 8080)

    assert "is not working" in str(exc_info.value)
    assert len(pool) == 0  # Should not be added


def test_add_proxy_without_check_adds_immediately():
    """Test that without check_on_add, proxy is added immediately."""
    pool = ProxyPool(check_on_add=False)

    start_time = time.time()
    proxy = pool.add_proxy("fast-proxy.com", 8080)
    elapsed = time.time() - start_time

    # Should be instant (no HTTP check)
    assert elapsed < 0.05
    assert len(pool) == 1
    assert proxy.host == "fast-proxy.com"
    assert proxy.port == 8080


def test_double_checked_locking_prevents_race_condition():
    """
    Test that double-checked locking prevents race conditions.

    Scenario:
    1. Thread A checks for duplicates - none found
    2. Thread B checks for duplicates - none found
    3. Thread A adds proxy
    4. Thread B tries to add same proxy - should fail
    """
    pool = ProxyPool(check_on_add=False)
    barrier = threading.Barrier(2)  # Synchronization point
    results = []

    def add_with_barrier():
        # Wait for both threads to reach this point
        barrier.wait()

        try:
            # Both threads will try to add at the same time
            pool.add_proxy("race-proxy.com", 8080)
            results.append("success")
        except ValueError:
            results.append("duplicate")

    t1 = threading.Thread(target=add_with_barrier)
    t2 = threading.Thread(target=add_with_barrier)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # One should succeed, one should fail
    assert "success" in results
    assert "duplicate" in results
    assert len(pool) == 1


@patch('src.http_client.utils.proxy_manager.requests.get')
def test_concurrent_check_all_proxies(mock_get):
    """Test that check_all_proxies works correctly with concurrent adds."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    pool = ProxyPool(check_on_add=False)  # Add without check first

    # Add proxies
    for i in range(5):
        pool.add_proxy(f"proxy{i}.com", 8080 + i)

    # Check all in parallel
    results = pool.check_all_proxies(max_workers=5)

    assert results["total"] == 5
    assert results["working"] == 5
    assert results["failed"] == 0
    assert mock_get.call_count == 5
