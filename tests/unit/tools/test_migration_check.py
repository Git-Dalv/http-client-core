"""Tests for migration checker tool."""

import tempfile
from pathlib import Path

import pytest

from src.http_client.tools.migration_check import (
    check_file,
    check_path,
    DeprecationChecker,
    DEPRECATED_IMPORTS,
    DEPRECATED_PARAMS
)


class TestDeprecationChecker:
    """Tests for DeprecationChecker AST visitor."""

    def test_finds_deprecated_import_loggingplugin(self, tmp_path):
        """Test detection of LoggingPlugin import."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from http_client.plugins import LoggingPlugin

client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(LoggingPlugin())
""")

        issues = check_file(test_file)

        # Should find import and usage
        assert len(issues) >= 1
        assert any("LoggingPlugin" in issue for _, issue, _ in issues)

    def test_finds_deprecated_import_from(self, tmp_path):
        """Test detection of deprecated imports in from...import statements."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from http_client.plugins import LoggingPlugin, MonitoringPlugin
""")

        issues = check_file(test_file)

        assert len(issues) >= 1
        assert any("LoggingPlugin" in issue for _, issue, _ in issues)

    def test_finds_deprecated_param_max_retries(self, tmp_path):
        """Test detection of deprecated max_retries parameter."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from http_client import HTTPClient

client = HTTPClient(
    base_url="https://api.example.com",
    max_retries=5
)
""")

        issues = check_file(test_file)

        assert len(issues) >= 1
        assert any("max_retries" in issue for _, issue, _ in issues)

    def test_finds_multiple_deprecated_params(self, tmp_path):
        """Test detection of multiple deprecated parameters."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from http_client import HTTPClient

client = HTTPClient(
    base_url="https://api.example.com",
    max_retries=3,
    pool_connections=20,
    verify_ssl=False
)
""")

        issues = check_file(test_file)

        # Should find all 3 deprecated parameters
        assert len(issues) >= 3
        assert any("max_retries" in issue for _, issue, _ in issues)
        assert any("pool_connections" in issue for _, issue, _ in issues)
        assert any("verify_ssl" in issue for _, issue, _ in issues)

    def test_finds_add_plugin_with_deprecated_plugin(self, tmp_path):
        """Test detection of add_plugin() with deprecated plugin."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from http_client import HTTPClient
from http_client.plugins import LoggingPlugin

client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(LoggingPlugin())
""")

        issues = check_file(test_file)

        # Should find import and usage
        assert len(issues) >= 2
        issue_texts = [issue for _, issue, _ in issues]
        assert any("LoggingPlugin" in text for text in issue_texts)

    def test_ignores_non_deprecated_imports(self, tmp_path):
        """Test that non-deprecated imports are not flagged."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from http_client import HTTPClient
from http_client.plugins import MonitoringPlugin

client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(MonitoringPlugin())
""")

        issues = check_file(test_file)

        # Should find no issues
        assert len(issues) == 0

    def test_ignores_non_deprecated_params(self, tmp_path):
        """Test that non-deprecated parameters are not flagged."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from http_client import HTTPClient
from http_client.core.config import HTTPClientConfig

config = HTTPClientConfig.create(
    base_url="https://api.example.com",
    timeout=30
)
client = HTTPClient(config=config)
""")

        issues = check_file(test_file)

        # Should find no issues
        assert len(issues) == 0

    def test_provides_suggestions(self, tmp_path):
        """Test that checker provides helpful suggestions."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from http_client.plugins import LoggingPlugin
""")

        issues = check_file(test_file)

        assert len(issues) >= 1
        _, _, suggestion = issues[0]
        assert "HTTPClientConfig.logging" in suggestion

    def test_reports_correct_line_numbers(self, tmp_path):
        """Test that line numbers are reported correctly."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""# Line 1
# Line 2
from http_client import HTTPClient  # Line 3
from http_client.plugins import LoggingPlugin  # Line 4
# Line 5
client = HTTPClient(base_url="...", max_retries=3)  # Line 6
""")

        issues = check_file(test_file)

        line_numbers = [line for line, _, _ in issues]

        # LoggingPlugin import on line 4
        assert 4 in line_numbers

        # max_retries parameter on line 6
        assert 6 in line_numbers


class TestCheckFile:
    """Tests for check_file function."""

    def test_checks_python_file(self, tmp_path):
        """Test checking a single Python file."""
        test_file = tmp_path / "app.py"
        test_file.write_text("""
from http_client import HTTPClient

client = HTTPClient(base_url="...", max_retries=3)
""")

        issues = check_file(test_file)
        assert len(issues) >= 1

    def test_handles_syntax_error(self, tmp_path):
        """Test handling of files with syntax errors."""
        test_file = tmp_path / "bad.py"
        test_file.write_text("""
def broken(
    # Missing closing parenthesis
""")

        with pytest.raises(SyntaxError):
            check_file(test_file)

    def test_handles_non_existent_file(self, tmp_path):
        """Test handling of non-existent files."""
        test_file = tmp_path / "nonexistent.py"

        with pytest.raises(IOError):
            check_file(test_file)


class TestCheckPath:
    """Tests for check_path function."""

    def test_checks_single_file(self, tmp_path):
        """Test checking a single file path."""
        test_file = tmp_path / "app.py"
        test_file.write_text("""
from http_client import HTTPClient

client = HTTPClient(base_url="...", verify_ssl=False)
""")

        results = check_path(test_file, recursive=False)

        assert test_file in results
        assert len(results[test_file]) >= 1

    def test_checks_directory_non_recursive(self, tmp_path):
        """Test checking a directory without recursion."""
        # Create files in directory
        (tmp_path / "file1.py").write_text("""
from http_client.plugins import LoggingPlugin
""")
        (tmp_path / "file2.py").write_text("""
from http_client import HTTPClient
client = HTTPClient(base_url="...", max_retries=3)
""")

        # Create subdirectory (should be ignored)
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file3.py").write_text("""
from http_client.plugins import LoggingPlugin
""")

        results = check_path(tmp_path, recursive=False)

        # Should find files in root, not in subdirectory
        assert len(results) == 2
        assert all(path.parent == tmp_path for path in results.keys())

    def test_checks_directory_recursive(self, tmp_path):
        """Test checking a directory recursively."""
        # Create files in directory
        (tmp_path / "file1.py").write_text("""
from http_client.plugins import LoggingPlugin
""")

        # Create subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.py").write_text("""
from http_client import HTTPClient
client = HTTPClient(base_url="...", max_retries=3)
""")

        # Create nested subdirectory
        nested = subdir / "nested"
        nested.mkdir()
        (nested / "file3.py").write_text("""
from http_client.plugins import LoggingPlugin
""")

        results = check_path(tmp_path, recursive=True)

        # Should find all 3 files
        assert len(results) == 3

    def test_ignores_non_python_files(self, tmp_path):
        """Test that non-Python files are ignored."""
        (tmp_path / "test.py").write_text("""
from http_client.plugins import LoggingPlugin
""")
        (tmp_path / "README.md").write_text("# README")
        (tmp_path / "data.json").write_text('{"key": "value"}')
        (tmp_path / "script.sh").write_text("#!/bin/bash\necho test")

        results = check_path(tmp_path, recursive=False)

        # Should only find the .py file
        assert len(results) == 1
        assert list(results.keys())[0].suffix == ".py"

    def test_empty_directory(self, tmp_path):
        """Test checking an empty directory."""
        results = check_path(tmp_path, recursive=False)

        assert len(results) == 0

    def test_directory_with_no_issues(self, tmp_path):
        """Test directory with only clean code."""
        (tmp_path / "clean.py").write_text("""
from http_client import HTTPClient
from http_client.core.config import HTTPClientConfig

config = HTTPClientConfig.create(base_url="...")
client = HTTPClient(config=config)
""")

        results = check_path(tmp_path, recursive=False)

        assert len(results) == 0


class TestDeprecatedPatterns:
    """Tests for specific deprecated patterns."""

    def test_all_deprecated_imports_detected(self, tmp_path):
        """Test that all deprecated imports are detected."""
        for deprecated_name in DEPRECATED_IMPORTS.keys():
            test_file = tmp_path / f"test_{deprecated_name}.py"
            test_file.write_text(f"""
from http_client.plugins import {deprecated_name}
""")

            issues = check_file(test_file)
            assert len(issues) >= 1, f"Failed to detect {deprecated_name}"
            assert any(deprecated_name in issue for _, issue, _ in issues)

    def test_all_deprecated_params_detected(self, tmp_path):
        """Test that all deprecated parameters are detected."""
        for param_name in DEPRECATED_PARAMS.keys():
            test_file = tmp_path / f"test_{param_name}.py"
            test_file.write_text(f"""
from http_client import HTTPClient

client = HTTPClient(base_url="...", {param_name}=True)
""")

            issues = check_file(test_file)
            assert len(issues) >= 1, f"Failed to detect {param_name}"
            assert any(param_name in issue for _, issue, _ in issues)


class TestIntegration:
    """Integration tests for migration checker."""

    def test_realistic_project_structure(self, tmp_path):
        """Test checking a realistic project structure."""
        # Create project structure
        src = tmp_path / "src"
        src.mkdir()

        # Old-style code with deprecated APIs
        (src / "old_client.py").write_text("""
from http_client import HTTPClient
from http_client.plugins import LoggingPlugin

def create_client():
    client = HTTPClient(
        base_url="https://api.example.com",
        max_retries=3,
        pool_connections=20,
        verify_ssl=False
    )
    client.add_plugin(LoggingPlugin())
    return client
""")

        # New-style code (clean)
        (src / "new_client.py").write_text("""
from http_client import HTTPClient
from http_client.core.config import HTTPClientConfig, RetryConfig

def create_client():
    config = HTTPClientConfig.create(
        base_url="https://api.example.com",
        retry=RetryConfig(max_attempts=3)
    )
    return HTTPClient(config=config)
""")

        # Tests directory
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_client.py").write_text("""
from src.old_client import create_client

def test_client():
    client = create_client()
    assert client is not None
""")

        results = check_path(tmp_path, recursive=True)

        # Should find issues in old_client.py
        old_client_path = src / "old_client.py"
        assert old_client_path in results
        assert len(results[old_client_path]) >= 4  # Import + 3 params + usage

        # new_client.py should be clean
        new_client_path = src / "new_client.py"
        assert new_client_path not in results

    def test_mixed_import_styles(self, tmp_path):
        """Test file with both deprecated and non-deprecated imports."""
        test_file = tmp_path / "mixed.py"
        test_file.write_text("""
from http_client import HTTPClient
from http_client.plugins import LoggingPlugin, MonitoringPlugin
from http_client.core.config import HTTPClientConfig

# Using deprecated
client1 = HTTPClient(base_url="...", max_retries=3)
client1.add_plugin(LoggingPlugin())

# Using new style
config = HTTPClientConfig.create(base_url="...")
client2 = HTTPClient(config=config)
client2.add_plugin(MonitoringPlugin())  # Not deprecated
""")

        issues = check_file(test_file)

        # Should find LoggingPlugin import, max_retries param, and LoggingPlugin usage
        # Should NOT find MonitoringPlugin
        assert len(issues) >= 3
        issue_texts = [issue for _, issue, _ in issues]
        assert any("LoggingPlugin" in text for text in issue_texts)
        assert any("max_retries" in text for text in issue_texts)
        assert not any("MonitoringPlugin" in text and "deprecated" in text.lower() for text in issue_texts)
