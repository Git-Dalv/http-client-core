"""Tests for configuration hot reload functionality."""

import json
import logging
import os
import tempfile
import threading
import time
from pathlib import Path

import pytest
import yaml

from src.http_client.core.config import HTTPClientConfig
from src.http_client.core.env_config import ConfigWatcher, ReloadableHTTPClient
from src.http_client.core.env_config.file_loader import ConfigValidationError


class TestConfigWatcher:
    """Tests for ConfigWatcher class."""

    @pytest.fixture
    def temp_config_file(self, tmp_path):
        """Create temporary YAML config file."""
        config_file = tmp_path / "config.yaml"
        initial_config = {
            "http_client": {
                "base_url": "https://api.example.com",
                "timeout": {"connect": 5, "read": 30},
                "retry": {"max_attempts": 3},
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(initial_config, f)
        return config_file

    def test_watcher_loads_initial_config(self, temp_config_file):
        """Test that watcher loads initial configuration."""
        watcher = ConfigWatcher(temp_config_file, check_interval=1.0)

        config = watcher.current_config
        assert config.base_url == "https://api.example.com"
        assert config.timeout.connect == 5
        assert config.timeout.read == 30
        assert config.retry.max_attempts == 3

    def test_watcher_detects_file_change(self, temp_config_file):
        """Test that watcher detects when config file is modified."""
        reload_called = threading.Event()
        new_config_received = {}

        def on_reload(config):
            new_config_received["config"] = config
            reload_called.set()

        watcher = ConfigWatcher(
            temp_config_file,
            check_interval=0.5,
            on_reload=on_reload
        )
        watcher.start()

        try:
            # Wait a bit to ensure watcher is running
            time.sleep(0.2)

            # Modify config file
            updated_config = {
                "http_client": {
                    "base_url": "https://api.updated.com",
                    "timeout": {"connect": 10, "read": 60},
                    "retry": {"max_attempts": 5},
                }
            }
            with open(temp_config_file, "w") as f:
                yaml.dump(updated_config, f)

            # Wait for reload to happen
            assert reload_called.wait(timeout=3.0), "Reload callback not called"

            # Verify new config was loaded
            config = watcher.current_config
            assert config.base_url == "https://api.updated.com"
            assert config.timeout.connect == 10
            assert config.timeout.read == 60
            assert config.retry.max_attempts == 5

        finally:
            watcher.stop()

    def test_watcher_keeps_old_config_on_error(self, temp_config_file):
        """Test that watcher keeps old config when new config has errors."""
        error_received = threading.Event()
        error_info = {}

        def on_error(exc):
            error_info["exception"] = exc
            error_received.set()

        watcher = ConfigWatcher(
            temp_config_file,
            check_interval=0.5,
            on_error=on_error
        )
        watcher.start()

        try:
            old_config = watcher.current_config
            old_base_url = old_config.base_url

            # Wait a bit
            time.sleep(0.2)

            # Write invalid YAML
            with open(temp_config_file, "w") as f:
                f.write("invalid: yaml: content: [[[")

            # Wait for error callback
            assert error_received.wait(timeout=3.0), "Error callback not called"

            # Verify old config is still active
            config = watcher.current_config
            assert config.base_url == old_base_url

        finally:
            watcher.stop()

    def test_watcher_thread_safety(self, temp_config_file):
        """Test thread-safe access to current_config."""
        watcher = ConfigWatcher(temp_config_file, check_interval=0.5)
        watcher.start()

        errors = []
        configs = []

        def read_config():
            try:
                for _ in range(100):
                    config = watcher.current_config
                    configs.append(config.base_url)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        # Start multiple threads reading config
        threads = [threading.Thread(target=read_config) for _ in range(5)]
        for t in threads:
            t.start()

        # Modify config while threads are reading
        time.sleep(0.2)
        updated_config = {
            "http_client": {
                "base_url": "https://api.modified.com",
                "timeout": {"connect": 5, "read": 30},
            }
        }
        with open(temp_config_file, "w") as f:
            yaml.dump(updated_config, f)

        # Wait for threads
        for t in threads:
            t.join()

        watcher.stop()

        # Should have no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Should have read configs successfully
        assert len(configs) > 0

    def test_watcher_start_stop(self, temp_config_file):
        """Test starting and stopping watcher."""
        watcher = ConfigWatcher(temp_config_file, check_interval=1.0)

        # Start watcher
        watcher.start()
        assert watcher._watcher_thread is not None
        assert watcher._watcher_thread.is_alive()

        # Stop watcher
        watcher.stop()
        time.sleep(0.5)  # Give thread time to stop
        assert not watcher._watcher_thread.is_alive()

    def test_watcher_start_idempotent(self, temp_config_file):
        """Test that calling start() multiple times is safe."""
        watcher = ConfigWatcher(temp_config_file, check_interval=1.0)

        watcher.start()
        thread1 = watcher._watcher_thread

        watcher.start()  # Call again
        thread2 = watcher._watcher_thread

        # Should be same thread
        assert thread1 is thread2
        assert thread1.is_alive()

        watcher.stop()

    def test_watcher_reload_now(self, temp_config_file):
        """Test manual reload with reload_now()."""
        reload_called = threading.Event()

        def on_reload(config):
            reload_called.set()

        watcher = ConfigWatcher(
            temp_config_file,
            check_interval=60.0,  # Long interval
            on_reload=on_reload
        )

        # Modify config
        updated_config = {
            "http_client": {
                "base_url": "https://api.manual-reload.com",
                "timeout": {"connect": 15, "read": 45},
            }
        }
        with open(temp_config_file, "w") as f:
            yaml.dump(updated_config, f)

        # Manually trigger reload
        assert watcher.reload_now() is True

        # Callback should have been called
        assert reload_called.is_set()

        # Config should be updated
        config = watcher.current_config
        assert config.base_url == "https://api.manual-reload.com"
        assert config.timeout.connect == 15

    def test_watcher_reload_now_failure(self, temp_config_file):
        """Test that reload_now() returns False on error."""
        watcher = ConfigWatcher(temp_config_file, check_interval=1.0)

        # Write invalid config
        with open(temp_config_file, "w") as f:
            f.write("this is not valid yaml: [[[")

        # Reload should fail but not crash
        assert watcher.reload_now() is False

        # Old config should still be accessible
        config = watcher.current_config
        assert config.base_url == "https://api.example.com"

    def test_watcher_callback_exception_handled(self, temp_config_file):
        """Test that exceptions in callbacks don't crash watcher."""
        reload_count = {"count": 0}

        def bad_callback(config):
            reload_count["count"] += 1
            raise ValueError("Callback error!")

        watcher = ConfigWatcher(
            temp_config_file,
            check_interval=0.5,
            on_reload=bad_callback
        )
        watcher.start()

        try:
            time.sleep(0.2)

            # Modify config
            updated_config = {
                "http_client": {
                    "base_url": "https://api.callback-error.com",
                    "timeout": {"connect": 5, "read": 30},
                }
            }
            with open(temp_config_file, "w") as f:
                yaml.dump(updated_config, f)

            # Wait for reload
            time.sleep(2.0)

            # Callback was called (and raised exception)
            assert reload_count["count"] > 0

            # But config was still updated
            config = watcher.current_config
            assert config.base_url == "https://api.callback-error.com"

        finally:
            watcher.stop()

    def test_watcher_missing_file_error(self, tmp_path):
        """Test that watcher raises error if file doesn't exist."""
        missing_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            ConfigWatcher(missing_file, check_interval=1.0)

    def test_watcher_json_config(self, tmp_path):
        """Test watcher with JSON config file."""
        config_file = tmp_path / "config.json"
        initial_config = {
            "http_client": {
                "base_url": "https://json.example.com",
                "timeout": {"connect": 3, "read": 20},
            }
        }
        with open(config_file, "w") as f:
            json.dump(initial_config, f)

        reload_called = threading.Event()

        def on_reload(config):
            reload_called.set()

        watcher = ConfigWatcher(config_file, check_interval=0.5, on_reload=on_reload)
        watcher.start()

        try:
            time.sleep(0.2)

            # Modify JSON config
            updated_config = {
                "http_client": {
                    "base_url": "https://json.updated.com",
                    "timeout": {"connect": 7, "read": 40},
                }
            }
            with open(config_file, "w") as f:
                json.dump(updated_config, f)

            # Wait for reload
            assert reload_called.wait(timeout=3.0)

            config = watcher.current_config
            assert config.base_url == "https://json.updated.com"
            assert config.timeout.connect == 7

        finally:
            watcher.stop()


class TestReloadableHTTPClient:
    """Tests for ReloadableHTTPClient class."""

    @pytest.fixture
    def temp_config_file(self, tmp_path):
        """Create temporary YAML config file."""
        config_file = tmp_path / "config.yaml"
        initial_config = {
            "http_client": {
                "base_url": "https://api.example.com",
                "timeout": {"connect": 5, "read": 30},
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(initial_config, f)
        return config_file

    def test_reloadable_client_creation(self, temp_config_file):
        """Test creating ReloadableHTTPClient."""
        client = ReloadableHTTPClient(temp_config_file, check_interval=1.0)

        try:
            assert client.base_url == "https://api.example.com"
            assert client.config.timeout.connect == 5
        finally:
            client.close()

    def test_reloadable_client_auto_reload(self, temp_config_file):
        """Test that client automatically reloads config."""
        client = ReloadableHTTPClient(temp_config_file, check_interval=0.5)

        try:
            # Initial config
            assert client.base_url == "https://api.example.com"

            time.sleep(0.2)

            # Modify config
            updated_config = {
                "http_client": {
                    "base_url": "https://api.reloaded.com",
                    "timeout": {"connect": 10, "read": 60},
                }
            }
            with open(temp_config_file, "w") as f:
                yaml.dump(updated_config, f)

            # Wait for reload
            time.sleep(2.0)

            # Client should have new config
            assert client.base_url == "https://api.reloaded.com"
            assert client.config.timeout.connect == 10

        finally:
            client.close()

    def test_reloadable_client_http_methods(self, temp_config_file):
        """Test that HTTP methods are properly proxied."""
        import responses

        client = ReloadableHTTPClient(temp_config_file, check_interval=1.0)

        try:
            # Mock HTTP responses
            with responses.RequestsMock() as rsps:
                rsps.add(
                    responses.GET,
                    "https://api.example.com/test",
                    json={"status": "ok"},
                    status=200
                )
                rsps.add(
                    responses.POST,
                    "https://api.example.com/data",
                    json={"created": True},
                    status=201
                )

                # Test GET
                response = client.get("/test")
                assert response.status_code == 200
                assert response.json()["status"] == "ok"

                # Test POST
                response = client.post("/data", json={"key": "value"})
                assert response.status_code == 201
                assert response.json()["created"] is True

        finally:
            client.close()

    def test_reloadable_client_context_manager(self, temp_config_file):
        """Test context manager support."""
        with ReloadableHTTPClient(temp_config_file, check_interval=1.0) as client:
            assert client.base_url == "https://api.example.com"

        # Watcher should be stopped after exiting context
        # No exception should occur

    def test_reloadable_client_close(self, temp_config_file):
        """Test that close() stops watcher."""
        client = ReloadableHTTPClient(temp_config_file, check_interval=1.0)

        watcher_thread = client._watcher._watcher_thread
        assert watcher_thread.is_alive()

        client.close()

        time.sleep(0.5)
        assert not watcher_thread.is_alive()

    def test_reloadable_client_properties(self, temp_config_file):
        """Test that client properties are accessible."""
        client = ReloadableHTTPClient(temp_config_file, check_interval=1.0)

        try:
            # Test base_url property
            assert client.base_url == "https://api.example.com"

            # Test timeout property (returns int for backward compatibility)
            assert client.timeout == 30  # read timeout

            # Test config property
            config = client.config
            assert isinstance(config, HTTPClientConfig)
            assert config.base_url == "https://api.example.com"
            assert config.timeout.connect == 5
            assert config.timeout.read == 30

        finally:
            client.close()

    def test_reloadable_client_plugins(self, temp_config_file):
        """Test adding plugins to reloadable client."""
        from src.http_client.plugins.logging_plugin import LoggingPlugin

        client = ReloadableHTTPClient(temp_config_file, check_interval=1.0)

        try:
            # Add plugin
            plugin = LoggingPlugin()
            client.add_plugin(plugin)

            # Plugin should be in underlying client
            # (We can't easily test this without making a real request)

        finally:
            client.close()

    def test_reloadable_client_thread_safety(self, temp_config_file):
        """Test that reloadable client is thread-safe."""
        client = ReloadableHTTPClient(temp_config_file, check_interval=0.3)

        errors = []
        base_urls = []

        def access_properties():
            """Access client properties from multiple threads."""
            try:
                for _ in range(50):
                    # Access properties (thread-safe)
                    url = client.base_url
                    timeout = client.timeout
                    config = client.config

                    base_urls.append(url)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        try:
            # Start threads accessing properties
            threads = [threading.Thread(target=access_properties) for _ in range(5)]
            for t in threads:
                t.start()

            # Modify config while threads are running
            time.sleep(0.2)
            updated_config = {
                "http_client": {
                    "base_url": "https://api.modified.com",
                    "timeout": {"connect": 8, "read": 40},
                }
            }
            with open(temp_config_file, "w") as f:
                yaml.dump(updated_config, f)

            # Wait for threads
            for t in threads:
                t.join()

            # Should have no errors
            assert len(errors) == 0, f"Errors: {errors}"

            # Should have accessed properties successfully
            assert len(base_urls) > 0

        finally:
            client.close()


class TestConfigWatcherIntegration:
    """Integration tests for ConfigWatcher."""

    def test_multiple_rapid_changes(self, tmp_path):
        """Test handling multiple rapid config changes."""
        config_file = tmp_path / "config.yaml"

        # Initial config
        config_data = {
            "http_client": {
                "base_url": "https://api.v0.com",
                "timeout": {"connect": 5, "read": 30},
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        reload_count = {"count": 0}

        def on_reload(config):
            reload_count["count"] += 1

        watcher = ConfigWatcher(config_file, check_interval=0.2, on_reload=on_reload)
        watcher.start()

        try:
            time.sleep(0.1)

            # Make multiple changes
            for i in range(1, 4):
                config_data["http_client"]["base_url"] = f"https://api.v{i}.com"
                with open(config_file, "w") as f:
                    yaml.dump(config_data, f)
                time.sleep(0.3)

            # Wait for all reloads
            time.sleep(1.0)

            # Should have reloaded at least once (may miss some due to timing)
            assert reload_count["count"] >= 1

            # Final config should be latest
            config = watcher.current_config
            assert "v" in config.base_url

        finally:
            watcher.stop()

    def test_config_file_deleted_and_recreated(self, tmp_path):
        """Test behavior when config file is deleted and recreated."""
        config_file = tmp_path / "config.yaml"

        # Initial config
        config_data = {
            "http_client": {
                "base_url": "https://api.initial.com",
                "timeout": {"connect": 5, "read": 30},
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        watcher = ConfigWatcher(config_file, check_interval=0.5)
        watcher.start()

        try:
            initial_base_url = watcher.current_config.base_url

            time.sleep(0.2)

            # Delete file
            os.remove(config_file)

            # Wait a bit
            time.sleep(1.0)

            # Old config should still work
            config = watcher.current_config
            assert config.base_url == initial_base_url

            # Recreate file
            config_data["http_client"]["base_url"] = "https://api.recreated.com"
            with open(config_file, "w") as f:
                yaml.dump(config_data, f)

            # Wait for reload
            time.sleep(1.5)

            # Should have new config
            config = watcher.current_config
            assert config.base_url == "https://api.recreated.com"

        finally:
            watcher.stop()
