"""
Tests for log formatters.

Tests JSONFormatter, TextFormatter, ColoredFormatter, and get_formatter.
"""

import json
import logging
import pytest
from src.http_client.core.logging.formatters import (
    JSONFormatter,
    TextFormatter,
    ColoredFormatter,
    get_formatter
)


class TestJSONFormatter:
    """Tests for JSONFormatter."""

    def test_basic_format(self):
        """JSONFormatter outputs valid JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "Test message"
        assert "timestamp" in data

    def test_format_with_extra_fields(self):
        """JSONFormatter includes extra fields."""
        formatter = JSONFormatter()
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

        output = formatter.format(record)
        data = json.loads(output)

        assert data["method"] == "GET"
        assert data["url"] == "https://api.com"
        assert data["status_code"] == 200

    def test_format_with_exception(self):
        """JSONFormatter includes exception info."""
        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=exc_info
            )

            output = formatter.format(record)
            data = json.loads(output)

            assert "exception" in data
            assert "ValueError" in data["exception"]
            assert "Test error" in data["exception"]

    def test_format_excludes_standard_fields(self):
        """JSONFormatter excludes standard logging fields from extras."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)
        data = json.loads(output)

        # These should not be in output as extra fields
        assert "pathname" not in data
        assert "lineno" not in data
        assert "funcName" not in data


class TestTextFormatter:
    """Tests for TextFormatter."""

    def test_basic_format(self):
        """TextFormatter outputs plain text."""
        formatter = TextFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)

        assert "[INFO]" in output
        assert "[test]" in output
        assert "Test message" in output

    def test_format_with_extra_fields(self):
        """TextFormatter appends extra fields."""
        formatter = TextFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Request completed",
            args=(),
            exc_info=None
        )
        record.method = "POST"
        record.status_code = 201

        output = formatter.format(record)

        assert "Request completed" in output
        assert "method=POST" in output
        assert "status_code=201" in output

    def test_format_without_extra_fields(self):
        """TextFormatter works without extra fields."""
        formatter = TextFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=10,
            msg="Warning message",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)

        assert "[WARNING]" in output
        assert "Warning message" in output
        # Should not have trailing space or "="
        assert not output.endswith(" ")


class TestColoredFormatter:
    """Tests for ColoredFormatter."""

    def test_basic_format_with_colors(self):
        """ColoredFormatter includes ANSI color codes."""
        formatter = ColoredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)

        # Should contain ANSI codes
        assert "\033[" in output
        # Should contain reset code
        assert "\033[0m" in output
        assert "Test message" in output

    def test_different_levels_different_colors(self):
        """ColoredFormatter uses different colors for different levels."""
        formatter = ColoredFormatter()

        levels = [
            (logging.DEBUG, "\033[36m"),    # Cyan
            (logging.INFO, "\033[32m"),     # Green
            (logging.WARNING, "\033[33m"),  # Yellow
            (logging.ERROR, "\033[31m"),    # Red
            (logging.CRITICAL, "\033[1;31m"), # Bold Red
        ]

        for level, expected_color in levels:
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="test.py",
                lineno=10,
                msg="Test",
                args=(),
                exc_info=None
            )

            output = formatter.format(record)
            assert expected_color in output

    def test_format_with_extra_fields(self):
        """ColoredFormatter includes extra fields."""
        formatter = ColoredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )
        record.user_id = 123

        output = formatter.format(record)

        assert "user_id=123" in output

    def test_levelname_restored_after_format(self):
        """ColoredFormatter restores original levelname."""
        formatter = ColoredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )

        original_levelname = record.levelname
        formatter.format(record)

        # Levelname should be restored to original
        assert record.levelname == original_levelname
        assert "\033[" not in record.levelname


class TestGetFormatter:
    """Tests for get_formatter function."""

    def test_get_json_formatter(self):
        """get_formatter returns JSONFormatter for 'json'."""
        formatter = get_formatter("json")
        assert isinstance(formatter, JSONFormatter)

    def test_get_text_formatter(self):
        """get_formatter returns TextFormatter for 'text'."""
        formatter = get_formatter("text")
        assert isinstance(formatter, TextFormatter)

    def test_get_colored_formatter(self):
        """get_formatter returns ColoredFormatter for 'colored'."""
        formatter = get_formatter("colored")
        assert isinstance(formatter, ColoredFormatter)

    def test_get_formatter_case_insensitive(self):
        """get_formatter is case-insensitive."""
        assert isinstance(get_formatter("JSON"), JSONFormatter)
        assert isinstance(get_formatter("Text"), TextFormatter)
        assert isinstance(get_formatter("COLORED"), ColoredFormatter)

    def test_get_formatter_unknown_type(self):
        """get_formatter raises ValueError for unknown type."""
        with pytest.raises(ValueError) as exc_info:
            get_formatter("unknown")

        assert "Unknown format type" in str(exc_info.value)
        assert "unknown" in str(exc_info.value)
