"""
Circuit Breaker pattern implementation for fault tolerance.

Protects against cascading failures by temporarily blocking requests
when error rate exceeds threshold.
"""

import asyncio
import logging
import threading
import time
from enum import Enum
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .config import CircuitBreakerConfig

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests allowed
    OPEN = "open"          # Too many failures, requests blocked
    HALF_OPEN = "half_open"  # Testing recovery, limited requests allowed


class CircuitBreaker:
    """
    Circuit Breaker pattern implementation.

    Protects against cascading failures by temporarily blocking requests
    when error rate exceeds threshold.

    States:
        - CLOSED: Normal operation, all requests pass through
        - OPEN: Too many failures, requests blocked
        - HALF_OPEN: Recovery test, limited requests allowed

    Transitions:
        - CLOSED -> OPEN: failure_count >= failure_threshold
        - OPEN -> HALF_OPEN: after recovery_timeout
        - HALF_OPEN -> CLOSED: successful requests
        - HALF_OPEN -> OPEN: any failure

    Example:
        >>> config = CircuitBreakerConfig(
        ...     enabled=True,
        ...     failure_threshold=5,
        ...     recovery_timeout=30.0
        ... )
        >>> breaker = CircuitBreaker(config)
        >>>
        >>> if breaker.can_execute():
        ...     try:
        ...         response = make_request()
        ...         breaker.record_success()
        ...     except Exception as e:
        ...         breaker.record_failure()
        ...         raise
    """

    def __init__(self, config: 'CircuitBreakerConfig'):
        """
        Initialize circuit breaker.

        Args:
            config: CircuitBreakerConfig instance
        """
        self._config = config
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.Lock()

        logger.debug(
            "CircuitBreaker initialized: threshold=%d, timeout=%ds",
            config.failure_threshold,
            config.recovery_timeout
        )

    def can_execute(self) -> bool:
        """
        Check if request can be executed.

        Returns:
            True if request is allowed, False if circuit is open
        """
        with self._lock:
            # If disabled, always allow
            if not self._config.enabled:
                return True

            # Check for automatic state transitions
            self._check_state_transition()

            if self._state == CircuitState.CLOSED:
                return True

            elif self._state == CircuitState.OPEN:
                return False

            elif self._state == CircuitState.HALF_OPEN:
                # Allow limited number of calls in half-open state
                can_call = self._half_open_calls < self._config.half_open_max_calls
                if can_call:
                    self._half_open_calls += 1
                return can_call

            return False

    def record_success(self) -> None:
        """
        Record successful request.

        In HALF_OPEN state, successful requests move circuit to CLOSED.
        In CLOSED state, resets failure count.
        """
        with self._lock:
            if not self._config.enabled:
                return

            logger.debug("Circuit breaker: recording success (state=%s)", self._state.value)

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1

                # If we got enough successful calls, close the circuit
                if self._success_count >= self._config.half_open_max_calls:
                    logger.info(
                        "Circuit breaker HALF_OPEN -> CLOSED after %d successful calls",
                        self._success_count
                    )
                    self._reset()

            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                if self._failure_count > 0:
                    self._failure_count = 0
                    logger.debug("Circuit breaker: reset failure count")

    def record_failure(self, exception: Optional[Exception] = None) -> None:
        """
        Record failed request.

        Args:
            exception: Exception that caused the failure (optional)

        In CLOSED state, increments failure count and may open circuit.
        In HALF_OPEN state, immediately opens circuit.
        """
        with self._lock:
            if not self._config.enabled:
                return

            # Check if this exception should be excluded
            if exception and self._config.exclude_exceptions:
                if type(exception) in self._config.exclude_exceptions:
                    logger.debug(
                        "Circuit breaker: ignoring excluded exception %s",
                        type(exception).__name__
                    )
                    return

            logger.debug("Circuit breaker: recording failure (state=%s)", self._state.value)

            if self._state == CircuitState.CLOSED:
                self._failure_count += 1
                self._last_failure_time = time.time()

                # Check if we should open the circuit
                if self._failure_count >= self._config.failure_threshold:
                    logger.warning(
                        "Circuit breaker CLOSED -> OPEN after %d failures",
                        self._failure_count
                    )
                    self._state = CircuitState.OPEN

            elif self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open state reopens the circuit
                logger.warning("Circuit breaker HALF_OPEN -> OPEN due to failure")
                self._state = CircuitState.OPEN
                self._failure_count += 1
                self._last_failure_time = time.time()
                self._half_open_calls = 0
                self._success_count = 0

    def get_state(self) -> CircuitState:
        """
        Get current circuit state.

        Returns:
            Current CircuitState
        """
        with self._lock:
            self._check_state_transition()
            return self._state

    def get_stats(self) -> dict:
        """
        Get circuit breaker statistics.

        Returns:
            Dictionary with stats
        """
        with self._lock:
            self._check_state_transition()

            return {
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "half_open_calls": self._half_open_calls,
                "last_failure_time": self._last_failure_time,
                "enabled": self._config.enabled,
            }

    def reset(self) -> None:
        """
        Manually reset circuit breaker to CLOSED state.

        Useful for testing or manual recovery.
        """
        with self._lock:
            logger.info("Circuit breaker manually reset")
            self._reset()

    def _reset(self) -> None:
        """
        Internal reset method (not thread-safe, must be called with lock).
        """
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time = None

    def _check_state_transition(self) -> None:
        """
        Check for automatic state transitions (not thread-safe).

        OPEN -> HALF_OPEN: After recovery_timeout
        """
        if self._state == CircuitState.OPEN and self._last_failure_time is not None:
            elapsed = time.time() - self._last_failure_time

            if elapsed >= self._config.recovery_timeout:
                logger.info(
                    "Circuit breaker OPEN -> HALF_OPEN after %.1fs recovery timeout",
                    elapsed
                )
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                self._success_count = 0


class AsyncCircuitBreaker:
    """
    Async version of Circuit Breaker pattern implementation.

    Uses asyncio.Lock instead of threading.Lock for async compatibility.
    All methods are async to work properly with asyncio event loop.

    States:
        - CLOSED: Normal operation, all requests pass through
        - OPEN: Too many failures, requests blocked
        - HALF_OPEN: Recovery test, limited requests allowed

    Example:
        >>> config = CircuitBreakerConfig(
        ...     enabled=True,
        ...     failure_threshold=5,
        ...     recovery_timeout=30.0
        ... )
        >>> breaker = AsyncCircuitBreaker(config)
        >>>
        >>> if await breaker.can_execute():
        ...     try:
        ...         response = await make_request()
        ...         await breaker.record_success()
        ...     except Exception as e:
        ...         await breaker.record_failure()
        ...         raise
    """

    def __init__(self, config: 'CircuitBreakerConfig'):
        """
        Initialize async circuit breaker.

        Args:
            config: CircuitBreakerConfig instance
        """
        self._config = config
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()  # Async lock for asyncio compatibility

        logger.debug(
            "AsyncCircuitBreaker initialized: threshold=%d, timeout=%ds",
            config.failure_threshold,
            config.recovery_timeout
        )

    async def can_execute(self) -> bool:
        """
        Check if request can be executed (async).

        Returns:
            True if request is allowed, False if circuit is open
        """
        async with self._lock:
            # If disabled, always allow
            if not self._config.enabled:
                return True

            # Check for automatic state transitions
            self._check_state_transition()

            if self._state == CircuitState.CLOSED:
                return True

            elif self._state == CircuitState.OPEN:
                return False

            elif self._state == CircuitState.HALF_OPEN:
                # Allow limited number of calls in half-open state
                can_call = self._half_open_calls < self._config.half_open_max_calls
                if can_call:
                    self._half_open_calls += 1
                return can_call

            return False

    async def record_success(self) -> None:
        """
        Record successful request (async).

        In HALF_OPEN state, successful requests move circuit to CLOSED.
        In CLOSED state, resets failure count.
        """
        async with self._lock:
            if not self._config.enabled:
                return

            logger.debug("Async circuit breaker: recording success (state=%s)", self._state.value)

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1

                # If we got enough successful calls, close the circuit
                if self._success_count >= self._config.half_open_max_calls:
                    logger.info(
                        "Async circuit breaker HALF_OPEN -> CLOSED after %d successful calls",
                        self._success_count
                    )
                    self._reset()

            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                if self._failure_count > 0:
                    self._failure_count = 0
                    logger.debug("Async circuit breaker: reset failure count")

    async def record_failure(self, exception: Optional[Exception] = None) -> None:
        """
        Record failed request (async).

        Args:
            exception: Exception that caused the failure (optional)

        In CLOSED state, increments failure count and may open circuit.
        In HALF_OPEN state, immediately opens circuit.
        """
        async with self._lock:
            if not self._config.enabled:
                return

            # Check if this exception should be excluded
            if exception and self._config.exclude_exceptions:
                if type(exception) in self._config.exclude_exceptions:
                    logger.debug(
                        "Async circuit breaker: ignoring excluded exception %s",
                        type(exception).__name__
                    )
                    return

            logger.debug("Async circuit breaker: recording failure (state=%s)", self._state.value)

            if self._state == CircuitState.CLOSED:
                self._failure_count += 1
                self._last_failure_time = time.time()

                # Check if we should open the circuit
                if self._failure_count >= self._config.failure_threshold:
                    logger.warning(
                        "Async circuit breaker CLOSED -> OPEN after %d failures",
                        self._failure_count
                    )
                    self._state = CircuitState.OPEN

            elif self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open state reopens the circuit
                logger.warning("Async circuit breaker HALF_OPEN -> OPEN due to failure")
                self._state = CircuitState.OPEN
                self._failure_count += 1
                self._last_failure_time = time.time()
                self._half_open_calls = 0
                self._success_count = 0

    async def get_state(self) -> CircuitState:
        """
        Get current circuit state (async).

        Returns:
            Current CircuitState
        """
        async with self._lock:
            self._check_state_transition()
            return self._state

    async def get_stats(self) -> dict:
        """
        Get circuit breaker statistics (async).

        Returns:
            Dictionary with stats
        """
        async with self._lock:
            self._check_state_transition()

            return {
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "half_open_calls": self._half_open_calls,
                "last_failure_time": self._last_failure_time,
                "enabled": self._config.enabled,
            }

    async def reset(self) -> None:
        """
        Manually reset circuit breaker to CLOSED state (async).

        Useful for testing or manual recovery.
        """
        async with self._lock:
            logger.info("Async circuit breaker manually reset")
            self._reset()

    def _reset(self) -> None:
        """
        Internal reset method (not thread-safe, must be called with lock).
        """
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time = None

    def _check_state_transition(self) -> None:
        """
        Check for automatic state transitions (not thread-safe).

        OPEN -> HALF_OPEN: After recovery_timeout
        """
        if self._state == CircuitState.OPEN and self._last_failure_time is not None:
            elapsed = time.time() - self._last_failure_time

            if elapsed >= self._config.recovery_timeout:
                logger.info(
                    "Async circuit breaker OPEN -> HALF_OPEN after %.1fs recovery timeout",
                    elapsed
                )
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                self._success_count = 0
