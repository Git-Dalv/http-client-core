"""
Tests for log filters.

Tests CorrelationIdFilter, ExtraFieldsFilter, RequestContextFilter,
and correlation ID management functions.
"""

import logging
import threading
import pytest
from src.http_client.core.logging.filters import (
    CorrelationIdFilter,
    ExtraFieldsFilter,
    RequestContextFilter,
    set_correlation_id,
    get_correlation_id,
    clear_correlation_id,
)


class TestCorrelationIdFunctions:
    """Tests for correlation ID management functions."""

    def test_set_and_get_correlation_id(self):
        """set_correlation_id and get_correlation_id work."""
        set_correlation_id("test-123")
        assert get_correlation_id() == "test-123"

        # Cleanup
        clear_correlation_id()

    def test_get_correlation_id_when_not_set(self):
        """get_correlation_id returns None when not set."""
        clear_correlation_id()
        assert get_correlation_id() is None

    def test_clear_correlation_id(self):
        """clear_correlation_id removes correlation ID."""
        set_correlation_id("test-456")
        assert get_correlation_id() == "test-456"

        clear_correlation_id()
        assert get_correlation_id() is None

    def test_clear_correlation_id_when_not_set(self):
        """clear_correlation_id works when ID is not set."""
        clear_correlation_id()
        clear_correlation_id()  # Should not raise
        assert get_correlation_id() is None

    def test_correlation_id_is_thread_local(self):
        """Correlation ID is thread-local (isolated per thread)."""
        clear_correlation_id()
        set_correlation_id("main-thread")

        # Track what the other thread sees
        other_thread_value = []

        def other_thread_func():
            # Should not see main thread's value
            other_thread_value.append(get_correlation_id())

            # Set own value
            set_correlation_id("other-thread")
            other_thread_value.append(get_correlation_id())

        thread = threading.Thread(target=other_thread_func)
        thread.start()
        thread.join()

        # Main thread should still have its value
        assert get_correlation_id() == "main-thread"

        # Other thread had None, then its own value
        assert other_thread_value == [None, "other-thread"]

        # Cleanup
        clear_correlation_id()


class TestCorrelationIdFilter:
    """Tests for CorrelationIdFilter."""

    def test_adds_correlation_id_when_set(self):
        """Filter adds correlation_id to record when set."""
        filter_instance = CorrelationIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )

        set_correlation_id("req-789")
        result = filter_instance.filter(record)

        assert result is True
        assert hasattr(record, "correlation_id")
        assert record.correlation_id == "req-789"

        # Cleanup
        clear_correlation_id()

    def test_does_not_add_when_not_set(self):
        """Filter does not add correlation_id when not set."""
        clear_correlation_id()

        filter_instance = CorrelationIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )

        result = filter_instance.filter(record)

        assert result is True
        assert not hasattr(record, "correlation_id")

    def test_filter_always_returns_true(self):
        """Filter always returns True (passes record through)."""
        filter_instance = CorrelationIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )

        # With correlation ID
        set_correlation_id("test")
        assert filter_instance.filter(record) is True

        # Without correlation ID
        clear_correlation_id()
        assert filter_instance.filter(record) is True


class TestExtraFieldsFilter:
    """Tests for ExtraFieldsFilter."""

    def test_adds_extra_fields(self):
        """Filter adds extra fields to record."""
        extra_fields = {
            "service": "api",
            "environment": "production",
            "version": "1.0.0"
        }
        filter_instance = ExtraFieldsFilter(extra_fields)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )

        result = filter_instance.filter(record)

        assert result is True
        assert record.service == "api"
        assert record.environment == "production"
        assert record.version == "1.0.0"

    def test_does_not_overwrite_existing_fields(self):
        """Filter does not overwrite existing record fields."""
        extra_fields = {"service": "api", "level": "CUSTOM"}
        filter_instance = ExtraFieldsFilter(extra_fields)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )
        record.service = "existing-service"

        filter_instance.filter(record)

        # Should not overwrite existing field
        assert record.service == "existing-service"

    def test_works_with_empty_dict(self):
        """Filter works with empty extra_fields."""
        filter_instance = ExtraFieldsFilter({})

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )

        result = filter_instance.filter(record)
        assert result is True

    def test_filter_always_returns_true(self):
        """Filter always returns True."""
        filter_instance = ExtraFieldsFilter({"key": "value"})
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )

        assert filter_instance.filter(record) is True


class TestRequestContextFilter:
    """Tests for RequestContextFilter."""

    def test_filter_passes_record_through(self):
        """Filter always returns True (passes record)."""
        filter_instance = RequestContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )

        result = filter_instance.filter(record)
        assert result is True

    def test_filter_with_http_context(self):
        """Filter works with HTTP context fields."""
        filter_instance = RequestContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Request completed",
            args=(),
            exc_info=None
        )
        record.method = "GET"
        record.url = "https://api.com"
        record.status_code = 200
        record.duration_ms = 150

        result = filter_instance.filter(record)

        assert result is True
        # Fields should still be present
        assert record.method == "GET"
        assert record.url == "https://api.com"
        assert record.status_code == 200
        assert record.duration_ms == 150

    def test_filter_without_http_context(self):
        """Filter works without HTTP context fields."""
        filter_instance = RequestContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Non-HTTP log",
            args=(),
            exc_info=None
        )

        result = filter_instance.filter(record)
        assert result is True
