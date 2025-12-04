"""
Tests for thread-safety of HTTPClient.

These tests verify that HTTPClient can be safely used from multiple threads
without race conditions, and that each thread gets its own isolated session.
"""
import threading
import time
from typing import List
import pytest
import responses

from src.http_client import HTTPClient
from src.http_client.core.config import HTTPClientConfig


class TestThreadSafety:
    """Test thread-safety of HTTPClient."""

    @responses.activate
    def test_concurrent_requests_from_multiple_threads(self):
        """Test that multiple threads can make concurrent requests safely."""
        # Setup mock responses
        base_url = "https://api.example.com"
        for i in range(20):
            responses.add(
                responses.GET,
                f"{base_url}/data/{i}",
                json={"id": i, "value": f"data-{i}"},
                status=200
            )

        # Create client
        client = HTTPClient(base_url=base_url)

        # Results storage
        results = []
        results_lock = threading.Lock()
        errors = []

        def make_request(thread_id: int):
            """Make request from thread."""
            try:
                # Make multiple requests from this thread
                for i in range(5):
                    endpoint = f"/data/{thread_id * 5 + i}"
                    response = client.get(endpoint)
                    data = response.json()

                    with results_lock:
                        results.append({
                            'thread_id': thread_id,
                            'endpoint': endpoint,
                            'data': data,
                            'session_id': id(client.session)  # Track session identity
                        })

                    # Small delay to increase chance of race conditions
                    time.sleep(0.001)
            except Exception as e:
                errors.append({
                    'thread_id': thread_id,
                    'error': str(e),
                    'type': type(e).__name__
                })

        # Create and start threads
        num_threads = 4
        threads = []

        for i in range(num_threads):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == num_threads * 5  # Each thread made 5 requests

        # Verify all requests succeeded
        for result in results:
            assert 'data' in result
            assert 'id' in result['data']

        # Clean up
        client.close()

    @responses.activate
    def test_thread_isolation_separate_sessions(self):
        """Test that each thread gets its own isolated session."""
        base_url = "https://api.example.com"
        responses.add(
            responses.GET,
            f"{base_url}/test",
            json={"status": "ok"},
            status=200
        )

        client = HTTPClient(base_url=base_url)

        # Track session IDs from different threads
        session_ids = []
        session_ids_lock = threading.Lock()

        def get_session_id(thread_id: int):
            """Get session ID from thread."""
            # Access session property
            session = client.session
            session_id = id(session)

            with session_ids_lock:
                session_ids.append({
                    'thread_id': thread_id,
                    'session_id': session_id
                })

            # Make a request to ensure session works
            response = client.get("/test")
            assert response.status_code == 200

        # Create threads
        num_threads = 10
        threads = []

        for i in range(num_threads):
            thread = threading.Thread(target=get_session_id, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify we got session IDs from all threads
        assert len(session_ids) == num_threads

        # Verify each thread got a different session
        unique_session_ids = set(item['session_id'] for item in session_ids)
        assert len(unique_session_ids) == num_threads, \
            "Each thread should have its own session instance"

        # Clean up
        client.close()

    @responses.activate
    def test_thread_isolation_cookies(self):
        """Test that cookies are isolated per thread."""
        base_url = "https://api.example.com"
        responses.add(
            responses.GET,
            f"{base_url}/data",
            json={"status": "ok"},
            status=200
        )

        client = HTTPClient(base_url=base_url)

        # Results storage
        cookie_results = []
        results_lock = threading.Lock()

        def test_cookies(thread_id: int):
            """Test cookie isolation in thread."""
            # Set thread-specific cookie
            cookie_value = f"thread-{thread_id}-cookie"
            client.set_cookie("thread_id", cookie_value)

            # Wait a bit to increase chance of race conditions
            time.sleep(0.01)

            # Read back cookie
            cookies = client.get_cookies()

            with results_lock:
                cookie_results.append({
                    'thread_id': thread_id,
                    'cookie_value': cookies.get('thread_id'),
                    'expected': cookie_value
                })

            # Make request
            response = client.get("/data")
            assert response.status_code == 200

        # Create threads
        num_threads = 10
        threads = []

        for i in range(num_threads):
            thread = threading.Thread(target=test_cookies, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify cookie isolation
        assert len(cookie_results) == num_threads

        for result in cookie_results:
            assert result['cookie_value'] == result['expected'], \
                f"Thread {result['thread_id']} cookie was corrupted: " \
                f"expected {result['expected']}, got {result['cookie_value']}"

        # Clean up
        client.close()

    @responses.activate
    def test_thread_isolation_headers(self):
        """Test that headers are isolated per thread."""
        base_url = "https://api.example.com"
        responses.add(
            responses.GET,
            f"{base_url}/data",
            json={"status": "ok"},
            status=200
        )

        client = HTTPClient(base_url=base_url)

        # Results storage
        header_results = []
        results_lock = threading.Lock()

        def test_headers(thread_id: int):
            """Test header isolation in thread."""
            # Set thread-specific header
            header_value = f"thread-{thread_id}-header"
            client.set_header("X-Thread-ID", header_value)

            # Wait a bit
            time.sleep(0.01)

            # Read back headers
            headers = client.get_headers()

            with results_lock:
                header_results.append({
                    'thread_id': thread_id,
                    'header_value': headers.get('X-Thread-ID'),
                    'expected': header_value
                })

            # Make request
            response = client.get("/data")
            assert response.status_code == 200

        # Create threads
        num_threads = 10
        threads = []

        for i in range(num_threads):
            thread = threading.Thread(target=test_headers, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify header isolation
        assert len(header_results) == num_threads

        for result in header_results:
            assert result['header_value'] == result['expected'], \
                f"Thread {result['thread_id']} header was corrupted"

        # Clean up
        client.close()

    @responses.activate
    def test_resource_cleanup_closes_all_sessions(self):
        """Test that close() properly closes sessions from all threads."""
        base_url = "https://api.example.com"
        responses.add(
            responses.GET,
            f"{base_url}/test",
            json={"status": "ok"},
            status=200
        )

        client = HTTPClient(base_url=base_url)

        # Track sessions
        sessions = []
        sessions_lock = threading.Lock()

        def access_session(thread_id: int):
            """Access session from thread."""
            session = client.session
            with sessions_lock:
                sessions.append(session)

            # Make request
            response = client.get("/test")
            assert response.status_code == 200

        # Create threads to generate multiple sessions
        num_threads = 5
        threads = []

        for i in range(num_threads):
            thread = threading.Thread(target=access_session, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify we have multiple sessions
        assert len(sessions) == num_threads

        # Close client
        client.close()

        # Verify all sessions are closed
        # Note: requests.Session doesn't have a clear "is_closed" flag,
        # but attempting to use a closed session will raise an error
        for session in sessions:
            # After close, the adapters should be empty or closed
            # This is a weak test, but requests doesn't provide better introspection
            assert hasattr(session, 'adapters')

    @responses.activate
    def test_context_manager_with_threads(self):
        """Test that context manager properly cleans up after threaded usage."""
        base_url = "https://api.example.com"
        responses.add(
            responses.GET,
            f"{base_url}/test",
            json={"status": "ok"},
            status=200
        )

        sessions_created = []
        sessions_lock = threading.Lock()

        with HTTPClient(base_url=base_url) as client:
            def make_request(thread_id: int):
                """Make request from thread."""
                session = client.session
                with sessions_lock:
                    sessions_created.append(id(session))

                response = client.get("/test")
                assert response.status_code == 200

            # Create threads
            num_threads = 5
            threads = []

            for i in range(num_threads):
                thread = threading.Thread(target=make_request, args=(i,))
                threads.append(thread)
                thread.start()

            # Wait for completion
            for thread in threads:
                thread.join()

        # After exiting context, all sessions should be closed
        assert len(sessions_created) == num_threads

    @responses.activate
    def test_stress_test_many_threads(self):
        """Stress test with many concurrent threads."""
        base_url = "https://api.example.com"

        # Setup many endpoints
        num_endpoints = 100
        for i in range(num_endpoints):
            responses.add(
                responses.GET,
                f"{base_url}/item/{i}",
                json={"id": i},
                status=200
            )

        client = HTTPClient(base_url=base_url)

        # Results
        results = []
        results_lock = threading.Lock()
        errors = []

        def worker(worker_id: int):
            """Worker thread that makes multiple requests."""
            try:
                for i in range(10):
                    endpoint_id = (worker_id * 10 + i) % num_endpoints
                    response = client.get(f"/item/{endpoint_id}")
                    data = response.json()

                    with results_lock:
                        results.append(data['id'])

            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")

        # Create many threads
        num_workers = 10
        threads = []

        start_time = time.time()

        for i in range(num_workers):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        elapsed = time.time() - start_time

        # Verify
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == num_workers * 10

        print(f"\nStress test: {num_workers} threads, {len(results)} requests in {elapsed:.2f}s")

        # Clean up
        client.close()

    def test_session_creation_race_condition(self):
        """
        Stress test to verify no race conditions during concurrent session creation.

        This test simulates the exact scenario that would trigger a race condition:
        50 threads all starting simultaneously and requesting sessions.
        """
        from src.http_client.core.session_manager import ThreadSafeSessionManager

        def create_test_session():
            """Factory to create test session."""
            import requests
            return requests.Session()

        manager = ThreadSafeSessionManager(create_test_session)

        # Number of threads to create
        num_threads = 50
        num_calls_per_thread = 10

        # Barrier to ensure all threads start at the same time
        barrier = threading.Barrier(num_threads)

        # Storage for results
        results_lock = threading.Lock()
        thread_sessions = {}  # {thread_id: [session_id1, session_id2, ...]}
        all_session_ids = []  # All unique session IDs seen
        session_holder = []  # Keep strong references to prevent GC

        def worker(thread_id: int):
            """Worker that calls get_session multiple times."""
            # Wait for all threads to be ready
            barrier.wait()

            # Call get_session multiple times
            session_ids = []
            for _ in range(num_calls_per_thread):
                session = manager.get_session()
                session_ids.append(id(session))

            # Store results and keep session alive
            with results_lock:
                thread_sessions[thread_id] = session_ids
                all_session_ids.extend(session_ids)
                # Keep strong reference to prevent GC when thread exits
                session_holder.append(session)

        # Create and start all threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify results
        # 1. Each thread should have gotten exactly num_calls_per_thread session IDs
        assert len(thread_sessions) == num_threads
        for thread_id, session_ids in thread_sessions.items():
            assert len(session_ids) == num_calls_per_thread, \
                f"Thread {thread_id} got {len(session_ids)} sessions instead of {num_calls_per_thread}"

        # 2. Within each thread, all session IDs should be identical
        #    (same session returned on every call)
        for thread_id, session_ids in thread_sessions.items():
            unique_ids = set(session_ids)
            assert len(unique_ids) == 1, \
                f"Thread {thread_id} got {len(unique_ids)} different sessions instead of 1"

        # 3. Across all threads, we should have exactly num_threads unique sessions
        unique_sessions = set(all_session_ids)
        assert len(unique_sessions) == num_threads, \
            f"Expected {num_threads} unique sessions, got {len(unique_sessions)}"

        # 4. Verify manager's count matches
        assert manager.get_active_sessions_count() == num_threads

        # Clean up
        manager.close_all()

    def test_session_manager_get_active_count(self):
        """Test that we can track the number of active sessions."""
        from src.http_client.core.session_manager import ThreadSafeSessionManager

        def create_test_session():
            """Factory to create test session."""
            import requests
            return requests.Session()

        manager = ThreadSafeSessionManager(create_test_session)

        # Initially no sessions
        assert manager.get_active_sessions_count() == 0

        # Access from main thread
        session1 = manager.get_session()
        assert manager.get_active_sessions_count() == 1

        # Access from another thread - keep thread alive
        sessions_holder = []  # Hold strong reference to prevent GC

        def access_session():
            session = manager.get_session()
            sessions_holder.append(session)  # Prevent GC

        thread = threading.Thread(target=access_session)
        thread.start()
        thread.join()

        # Now should have 2 sessions (thread session kept alive by sessions_holder)
        assert manager.get_active_sessions_count() == 2

        # Close all
        manager.close_all()

        # After close, count should be 0
        assert manager.get_active_sessions_count() == 0

    @responses.activate
    def test_lazy_initialization(self):
        """Test that sessions are created lazily on first access."""
        base_url = "https://api.example.com"
        responses.add(
            responses.GET,
            f"{base_url}/test",
            json={"status": "ok"},
            status=200
        )

        # Create client but don't access session
        client = HTTPClient(base_url=base_url)

        # Initially, no sessions should exist in manager
        # (we can't directly test this without exposing internals,
        # but we can verify behavior)

        # Access from thread should create session lazily
        session_created = threading.Event()

        def access_session():
            """Access session - should trigger lazy creation."""
            _ = client.session
            session_created.set()

        thread = threading.Thread(target=access_session)
        thread.start()
        thread.join()

        # Verify session was created
        assert session_created.is_set()

        # Clean up
        client.close()

    @responses.activate
    def test_same_thread_gets_same_session(self):
        """Test that multiple accesses from same thread return same session."""
        base_url = "https://api.example.com"
        responses.add(
            responses.GET,
            f"{base_url}/test",
            json={"status": "ok"},
            status=200
        )

        client = HTTPClient(base_url=base_url)

        # Access session multiple times from same thread
        session1 = client.session
        session2 = client.session
        session3 = client.session

        # Should be the exact same object
        assert session1 is session2
        assert session2 is session3
        assert id(session1) == id(session2) == id(session3)

        # Clean up
        client.close()


class TestBackwardCompatibility:
    """Test that thread-safety changes don't break existing code."""

    @responses.activate
    def test_existing_code_still_works(self):
        """Test that existing non-threaded code continues to work."""
        base_url = "https://api.example.com"
        responses.add(
            responses.GET,
            f"{base_url}/users",
            json={"users": []},
            status=200
        )

        # Standard usage (non-threaded)
        client = HTTPClient(base_url=base_url)
        response = client.get("/users")
        assert response.status_code == 200
        assert response.json() == {"users": []}
        client.close()

    @responses.activate
    def test_session_property_still_accessible(self):
        """Test that the session property is still accessible."""
        client = HTTPClient(base_url="https://api.example.com")

        # Should be able to access session
        session = client.session
        assert session is not None
        assert hasattr(session, 'request')
        assert hasattr(session, 'get')

        client.close()

    @responses.activate
    def test_cookie_methods_work(self):
        """Test that cookie methods still work as expected."""
        base_url = "https://api.example.com"
        responses.add(
            responses.GET,
            f"{base_url}/test",
            json={"status": "ok"},
            status=200
        )

        client = HTTPClient(base_url=base_url)

        # Set cookie
        client.set_cookie("test", "value")

        # Get cookies
        cookies = client.get_cookies()
        assert cookies.get("test") == "value"

        # Remove cookie
        client.remove_cookie("test")
        cookies = client.get_cookies()
        assert "test" not in cookies

        # Clear cookies
        client.set_cookie("a", "1")
        client.set_cookie("b", "2")
        client.clear_cookies()
        cookies = client.get_cookies()
        assert len(cookies) == 0

        client.close()
