"""
Tests for Circuit Breaker pattern implementation.
"""

import time
import threading
import pytest

from src.http_client.core.circuit_breaker import CircuitBreaker, CircuitState
from src.http_client.core.config import CircuitBreakerConfig
from src.http_client.core.exceptions import TimeoutError, BadRequestError


class TestCircuitBreakerInit:
    """Test CircuitBreaker initialization."""

    def test_init_with_config(self):
        """Test initialization with config."""
        config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=10,
            recovery_timeout=60.0
        )
        breaker = CircuitBreaker(config)

        assert breaker.get_state() == CircuitState.CLOSED
        stats = breaker.get_stats()
        assert stats['state'] == 'closed'
        assert stats['failure_count'] == 0
        assert stats['enabled'] is True

    def test_init_disabled(self):
        """Test initialization with disabled circuit breaker."""
        config = CircuitBreakerConfig(enabled=False)
        breaker = CircuitBreaker(config)

        # Should always allow requests when disabled
        assert breaker.can_execute() is True

        # Record failures should have no effect
        for _ in range(10):
            breaker.record_failure()

        assert breaker.can_execute() is True


class TestCircuitBreakerClosedToOpen:
    """Test CLOSED -> OPEN transition."""

    def test_transition_on_failure_threshold(self):
        """Test circuit opens after reaching failure threshold."""
        config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=5,
            recovery_timeout=30.0
        )
        breaker = CircuitBreaker(config)

        # Initially closed
        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker.can_execute() is True

        # Record failures below threshold
        for i in range(4):
            breaker.record_failure()
            assert breaker.get_state() == CircuitState.CLOSED
            assert breaker.can_execute() is True

        # 5th failure should open circuit
        breaker.record_failure()
        assert breaker.get_state() == CircuitState.OPEN
        assert breaker.can_execute() is False

    def test_excluded_exceptions_not_counted(self):
        """Test that excluded exceptions don't count as failures."""
        config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=3,
            exclude_exceptions=frozenset([BadRequestError])
        )
        breaker = CircuitBreaker(config)

        # Record excluded exceptions
        for _ in range(5):
            breaker.record_failure(BadRequestError("test", "http://example.com"))

        # Should still be closed (excluded exceptions don't count)
        assert breaker.get_state() == CircuitState.CLOSED

        # Now record non-excluded exceptions
        for _ in range(3):
            breaker.record_failure(TimeoutError("test", "http://example.com"))

        # Should be open now
        assert breaker.get_state() == CircuitState.OPEN


class TestCircuitBreakerOpenToHalfOpen:
    """Test OPEN -> HALF_OPEN transition."""

    def test_auto_transition_after_recovery_timeout(self):
        """Test automatic transition to HALF_OPEN after timeout."""
        config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=3,
            recovery_timeout=0.2  # 200ms for fast test
        )
        breaker = CircuitBreaker(config)

        # Open the circuit
        for _ in range(3):
            breaker.record_failure()

        assert breaker.get_state() == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.3)

        # Should transition to HALF_OPEN
        assert breaker.get_state() == CircuitState.HALF_OPEN
        assert breaker.can_execute() is True


class TestCircuitBreakerHalfOpenToClosed:
    """Test HALF_OPEN -> CLOSED transition."""

    def test_transition_on_success(self):
        """Test circuit closes after successful requests in HALF_OPEN."""
        config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=3,
            recovery_timeout=0.1,
            half_open_max_calls=3
        )
        breaker = CircuitBreaker(config)

        # Open the circuit
        for _ in range(3):
            breaker.record_failure()

        assert breaker.get_state() == CircuitState.OPEN

        # Wait for recovery
        time.sleep(0.2)
        assert breaker.get_state() == CircuitState.HALF_OPEN

        # Record successful requests
        for i in range(3):
            assert breaker.can_execute() is True
            breaker.record_success()

        # Should be closed now
        assert breaker.get_state() == CircuitState.CLOSED
        stats = breaker.get_stats()
        assert stats['failure_count'] == 0


class TestCircuitBreakerHalfOpenToOpen:
    """Test HALF_OPEN -> OPEN transition."""

    def test_transition_on_failure(self):
        """Test circuit reopens on failure in HALF_OPEN state."""
        config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=3,
            recovery_timeout=0.1,
            half_open_max_calls=3
        )
        breaker = CircuitBreaker(config)

        # Open the circuit
        for _ in range(3):
            breaker.record_failure()

        # Wait for recovery
        time.sleep(0.2)
        assert breaker.get_state() == CircuitState.HALF_OPEN

        # First call succeeds
        assert breaker.can_execute() is True
        breaker.record_success()

        # Second call fails - should reopen circuit
        assert breaker.can_execute() is True
        breaker.record_failure()

        # Circuit should be OPEN again
        assert breaker.get_state() == CircuitState.OPEN
        assert breaker.can_execute() is False


class TestCircuitBreakerHalfOpenLimits:
    """Test HALF_OPEN call limits."""

    def test_limited_calls_in_half_open(self):
        """Test that HALF_OPEN allows only limited calls."""
        config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=3,
            recovery_timeout=0.1,
            half_open_max_calls=2
        )
        breaker = CircuitBreaker(config)

        # Open the circuit
        for _ in range(3):
            breaker.record_failure()

        # Wait for recovery
        time.sleep(0.2)
        assert breaker.get_state() == CircuitState.HALF_OPEN

        # First two calls should be allowed
        assert breaker.can_execute() is True
        assert breaker.can_execute() is True

        # Third call should be blocked (max 2 calls)
        assert breaker.can_execute() is False


class TestCircuitBreakerReset:
    """Test manual reset."""

    def test_manual_reset(self):
        """Test manual reset to CLOSED state."""
        config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=3
        )
        breaker = CircuitBreaker(config)

        # Open the circuit
        for _ in range(3):
            breaker.record_failure()

        assert breaker.get_state() == CircuitState.OPEN

        # Manual reset
        breaker.reset()

        # Should be closed
        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker.can_execute() is True
        stats = breaker.get_stats()
        assert stats['failure_count'] == 0


class TestCircuitBreakerThreadSafety:
    """Test thread safety."""

    def test_concurrent_can_execute(self):
        """Test thread-safe can_execute calls."""
        config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=100,
            half_open_max_calls=10
        )
        breaker = CircuitBreaker(config)

        results = []
        errors = []

        def worker():
            try:
                for _ in range(100):
                    result = breaker.can_execute()
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # Run 10 threads concurrently
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0
        # All should return True (circuit is CLOSED)
        assert all(results)

    def test_concurrent_record_failure(self):
        """Test thread-safe record_failure calls."""
        config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=50,
            recovery_timeout=1.0
        )
        breaker = CircuitBreaker(config)

        errors = []

        def worker():
            try:
                for _ in range(10):
                    breaker.record_failure()
            except Exception as e:
                errors.append(e)

        # Run 10 threads (100 total failures)
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0

        # Circuit should be OPEN (100 failures > threshold 50)
        assert breaker.get_state() == CircuitState.OPEN


class TestCircuitBreakerStats:
    """Test statistics."""

    def test_get_stats(self):
        """Test get_stats returns correct information."""
        config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=5,
            recovery_timeout=30.0
        )
        breaker = CircuitBreaker(config)

        # Record some failures
        for _ in range(3):
            breaker.record_failure()

        stats = breaker.get_stats()

        assert stats['state'] == 'closed'
        assert stats['failure_count'] == 3
        assert stats['success_count'] == 0
        assert stats['enabled'] is True
        assert stats['last_failure_time'] is not None

        # Record success
        breaker.record_success()

        stats = breaker.get_stats()
        assert stats['failure_count'] == 0  # Reset on success in CLOSED state
