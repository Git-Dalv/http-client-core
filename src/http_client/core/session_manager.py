# src/http_client/core/session_manager.py
"""
Thread-safe session management for HTTPClient.

This module provides thread-local storage for requests.Session objects,
ensuring that each thread gets its own isolated session instance.
"""
import threading
from typing import Callable, Optional, Set
import weakref

import requests


class ThreadSafeSessionManager:
    """
    Manages thread-local requests.Session instances.

    Each thread gets its own Session object to avoid race conditions.
    Sessions are lazily initialized on first access per thread.

    Features:
        - Thread-local session isolation
        - Lazy initialization
        - Automatic cleanup of all sessions
        - Weak references to track sessions

    Example:
        >>> manager = ThreadSafeSessionManager(session_factory)
        >>> session = manager.get_session()  # Gets thread-local session
        >>> manager.close_all()  # Closes all sessions from all threads
    """

    def __init__(self, session_factory: Callable[[], requests.Session]):
        """
        Initialize the session manager.

        Args:
            session_factory: Callable that creates and configures a new Session
        """
        self._session_factory = session_factory
        self._local = threading.local()

        # Track all created sessions for cleanup (using weak references)
        self._all_sessions: Set[weakref.ref] = set()
        self._sessions_lock = threading.Lock()

    def get_session(self) -> requests.Session:
        """
        Get thread-local session, creating it lazily if needed.

        Returns:
            requests.Session instance for current thread
        """
        # Check if current thread already has a session
        if not hasattr(self._local, 'session') or self._local.session is None:
            # Create new session for this thread
            session = self._session_factory()
            self._local.session = session

            # Track this session for cleanup (weak reference to avoid memory leaks)
            with self._sessions_lock:
                # Create weak reference with callback to remove from set when GC'd
                ref = weakref.ref(session, self._cleanup_weak_ref)
                self._all_sessions.add(ref)

        return self._local.session

    def _cleanup_weak_ref(self, ref: weakref.ref):
        """
        Callback to remove dead weak reference from tracking set.

        Args:
            ref: Weak reference that was garbage collected
        """
        with self._sessions_lock:
            self._all_sessions.discard(ref)

    def close_current_session(self):
        """
        Close session for current thread only.

        This is useful for explicit cleanup in long-running threads.
        """
        if hasattr(self._local, 'session') and self._local.session is not None:
            try:
                self._local.session.close()
            except Exception:
                # Ignore errors during cleanup
                pass
            finally:
                self._local.session = None

    def close_all(self):
        """
        Close all sessions from all threads.

        This should be called when shutting down the HTTPClient.
        Safe to call multiple times.
        """
        # Close current thread's session first
        self.close_current_session()

        # Close all tracked sessions
        with self._sessions_lock:
            # Create a copy to avoid modification during iteration
            sessions_copy = list(self._all_sessions)

            for session_ref in sessions_copy:
                session = session_ref()
                if session is not None:
                    try:
                        session.close()
                    except Exception:
                        # Ignore errors during cleanup
                        pass

            # Clear the tracking set
            self._all_sessions.clear()

    def get_active_sessions_count(self) -> int:
        """
        Get number of active sessions across all threads.

        Returns:
            Count of active (not garbage collected) sessions
        """
        with self._sessions_lock:
            # Count only sessions that are still alive
            return sum(1 for ref in self._all_sessions if ref() is not None)

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close all sessions on context exit."""
        self.close_all()
        return False
