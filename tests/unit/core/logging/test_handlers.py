"""
Tests for log handlers.

Tests create_console_handler and create_file_handler.
"""

import logging
import os
import tempfile
from pathlib import Path
from logging.handlers import RotatingFileHandler
import pytest

from src.http_client.core.logging.handlers import (
    create_console_handler,
    create_file_handler
)
from src.http_client.core.logging.formatters import TextFormatter
from src.http_client.core.logging.filters import ExtraFieldsFilter


class TestCreateConsoleHandler:
    """Tests for create_console_handler function."""

    def test_creates_stream_handler(self):
        """create_console_handler returns StreamHandler."""
        formatter = TextFormatter()
        handler = create_console_handler(logging.INFO, formatter)

        assert isinstance(handler, logging.StreamHandler)

    def test_handler_has_correct_level(self):
        """Handler has correct log level."""
        formatter = TextFormatter()
        handler = create_console_handler(logging.DEBUG, formatter)

        assert handler.level == logging.DEBUG

    def test_handler_has_formatter(self):
        """Handler has the provided formatter."""
        formatter = TextFormatter()
        handler = create_console_handler(logging.INFO, formatter)

        assert handler.formatter is formatter

    def test_handler_writes_to_stdout(self):
        """Handler writes to stdout (not stderr)."""
        import sys
        formatter = TextFormatter()
        handler = create_console_handler(logging.INFO, formatter)

        assert handler.stream is sys.stdout

    def test_handler_with_filters(self):
        """Handler can have filters."""
        formatter = TextFormatter()
        filter1 = ExtraFieldsFilter({"service": "test"})
        filter2 = ExtraFieldsFilter({"env": "dev"})

        handler = create_console_handler(
            logging.INFO,
            formatter,
            filters=[filter1, filter2]
        )

        assert len(handler.filters) == 2
        assert filter1 in handler.filters
        assert filter2 in handler.filters

    def test_handler_without_filters(self):
        """Handler works without filters."""
        formatter = TextFormatter()
        handler = create_console_handler(logging.INFO, formatter, filters=None)

        assert len(handler.filters) == 0

    def test_handler_with_empty_filters_list(self):
        """Handler works with empty filters list."""
        formatter = TextFormatter()
        handler = create_console_handler(logging.INFO, formatter, filters=[])

        assert len(handler.filters) == 0


class TestCreateFileHandler:
    """Tests for create_file_handler function."""

    def test_creates_rotating_file_handler(self):
        """create_file_handler returns RotatingFileHandler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            formatter = TextFormatter()

            handler = create_file_handler(log_file, logging.INFO, formatter)

            assert isinstance(handler, RotatingFileHandler)

            # Cleanup
            handler.close()

    def test_handler_has_correct_level(self):
        """Handler has correct log level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            formatter = TextFormatter()

            handler = create_file_handler(log_file, logging.WARNING, formatter)

            assert handler.level == logging.WARNING

            handler.close()

    def test_handler_has_formatter(self):
        """Handler has the provided formatter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            formatter = TextFormatter()

            handler = create_file_handler(log_file, logging.INFO, formatter)

            assert handler.formatter is formatter

            handler.close()

    def test_creates_directory_if_not_exists(self):
        """Handler creates parent directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "subdir", "nested", "test.log")
            formatter = TextFormatter()

            handler = create_file_handler(log_file, logging.INFO, formatter)

            # Directory should be created
            assert os.path.exists(os.path.join(tmpdir, "subdir", "nested"))
            assert os.path.isdir(os.path.join(tmpdir, "subdir", "nested"))

            handler.close()

    def test_handler_with_custom_max_bytes(self):
        """Handler respects custom max_bytes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            formatter = TextFormatter()

            handler = create_file_handler(
                log_file,
                logging.INFO,
                formatter,
                max_bytes=5 * 1024 * 1024  # 5MB
            )

            assert handler.maxBytes == 5 * 1024 * 1024

            handler.close()

    def test_handler_with_default_max_bytes(self):
        """Handler uses default max_bytes (10MB)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            formatter = TextFormatter()

            handler = create_file_handler(log_file, logging.INFO, formatter)

            assert handler.maxBytes == 10 * 1024 * 1024

            handler.close()

    def test_handler_with_custom_backup_count(self):
        """Handler respects custom backup_count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            formatter = TextFormatter()

            handler = create_file_handler(
                log_file,
                logging.INFO,
                formatter,
                backup_count=10
            )

            assert handler.backupCount == 10

            handler.close()

    def test_handler_with_default_backup_count(self):
        """Handler uses default backup_count (5)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            formatter = TextFormatter()

            handler = create_file_handler(log_file, logging.INFO, formatter)

            assert handler.backupCount == 5

            handler.close()

    def test_handler_with_filters(self):
        """Handler can have filters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            formatter = TextFormatter()
            filter1 = ExtraFieldsFilter({"app": "test"})

            handler = create_file_handler(
                log_file,
                logging.INFO,
                formatter,
                filters=[filter1]
            )

            assert len(handler.filters) == 1
            assert filter1 in handler.filters

            handler.close()

    def test_handler_without_filters(self):
        """Handler works without filters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            formatter = TextFormatter()

            handler = create_file_handler(
                log_file,
                logging.INFO,
                formatter,
                filters=None
            )

            assert len(handler.filters) == 0

            handler.close()

    def test_handler_writes_to_file(self):
        """Handler actually writes logs to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            formatter = TextFormatter()

            handler = create_file_handler(log_file, logging.INFO, formatter)

            # Create logger and write log
            logger = logging.getLogger("test_file_handler")
            logger.setLevel(logging.INFO)
            logger.addHandler(handler)

            logger.info("Test log message")

            handler.close()

            # Check file exists and has content
            assert os.path.exists(log_file)
            with open(log_file, 'r') as f:
                content = f.read()
                assert "Test log message" in content

            # Cleanup
            logger.removeHandler(handler)

    def test_handler_encoding_is_utf8(self):
        """Handler uses UTF-8 encoding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            formatter = TextFormatter()

            handler = create_file_handler(log_file, logging.INFO, formatter)

            assert handler.encoding == 'utf-8'

            handler.close()
