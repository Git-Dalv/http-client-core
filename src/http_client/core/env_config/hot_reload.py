"""Hot reload configuration support for long-running processes.

This module provides functionality to automatically reload HTTPClient configuration
when the config file changes, without requiring application restart. Useful for
long-running workers, scrapers, and API clients.

Example:
    >>> from http_client import ReloadableHTTPClient
    >>>
    >>> # Automatic reload every 10 seconds
    >>> client = ReloadableHTTPClient("config.yaml", check_interval=10.0)
    >>> response = client.get("/api/data")  # Uses current config
    >>>
    >>> # Context manager support
    >>> with ReloadableHTTPClient("config.yaml") as client:
    ...     client.get("/health")

Example with manual control:
    >>> from http_client.core.env_config import ConfigWatcher
    >>>
    >>> watcher = ConfigWatcher(
    ...     "config.yaml",
    ...     on_reload=lambda cfg: print(f"New timeout: {cfg.timeout}"),
    ...     on_error=lambda e: print(f"Error: {e}")
    ... )
    >>> watcher.start()
    >>>
    >>> client = HTTPClient(config=watcher.current_config)
    >>> # Config automatically updates
    >>> watcher.stop()
"""

import logging
import os
import threading
import time
from pathlib import Path
from typing import Callable, Optional, Union

from ..config import HTTPClientConfig
from .file_loader import ConfigFileLoader

logger = logging.getLogger(__name__)


class ConfigWatcher:
    """Monitors config file for changes and applies them automatically.

    Thread-safe implementation that polls the file's modification time
    and reloads configuration when changes are detected.

    Attributes:
        config_path: Path to the configuration file
        check_interval: Seconds between file modification checks
        current_config: Currently active configuration (thread-safe)
    """

    def __init__(
        self,
        config_path: Union[str, Path],
        check_interval: float = 5.0,
        on_reload: Optional[Callable[[HTTPClientConfig], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        """Initialize configuration watcher.

        Args:
            config_path: Path to configuration file (YAML or JSON)
            check_interval: Seconds between file checks (default: 5.0)
            on_reload: Callback invoked after successful reload with new config
            on_error: Callback invoked when reload fails with exception

        Raises:
            FileNotFoundError: If config file doesn't exist
            ConfigValidationError: If initial config load fails
        """
        self.config_path = Path(config_path)
        self.check_interval = check_interval
        self.on_reload = on_reload
        self.on_error = on_error

        # Thread-safe config access
        self._config_lock = threading.RLock()
        self._config: Optional[HTTPClientConfig] = None

        # Watcher thread control
        self._stop_event = threading.Event()
        self._watcher_thread: Optional[threading.Thread] = None

        # Track file modification time
        self._last_mtime: Optional[float] = None

        # Load initial configuration
        self._load_config()

    def _load_config(self) -> bool:
        """Load or reload configuration from file.

        Returns:
            True if config was loaded successfully, False otherwise
        """
        try:
            new_config = ConfigFileLoader.from_file(self.config_path)

            with self._config_lock:
                old_config = self._config
                self._config = new_config
                self._last_mtime = os.path.getmtime(self.config_path)

            # Only trigger callback if this is a reload (not initial load)
            if old_config is not None and self.on_reload:
                try:
                    self.on_reload(new_config)
                except Exception as e:
                    logger.warning(f"on_reload callback failed: {e}")

            logger.info(f"Config loaded from {self.config_path}")
            return True

        except Exception as e:
            logger.warning(f"Config reload failed, keeping previous: {e}")

            if self.on_error:
                try:
                    self.on_error(e)
                except Exception as cb_error:
                    logger.warning(f"on_error callback failed: {cb_error}")

            # If this is initial load, re-raise
            if self._config is None:
                raise

            return False

    def _check_and_reload(self) -> None:
        """Check if file was modified and reload if necessary."""
        try:
            if not self.config_path.exists():
                logger.warning(f"Config file disappeared: {self.config_path}")
                return

            current_mtime = os.path.getmtime(self.config_path)

            if self._last_mtime is None or current_mtime > self._last_mtime:
                logger.debug(f"Config file modified, reloading: {self.config_path}")
                self._load_config()

        except Exception as e:
            logger.error(f"Error checking config file: {e}")

    def _watcher_loop(self) -> None:
        """Background thread that monitors file for changes."""
        logger.info(f"Config watcher started for {self.config_path} (interval: {self.check_interval}s)")

        while not self._stop_event.is_set():
            self._check_and_reload()

            # Use wait instead of sleep for faster shutdown
            self._stop_event.wait(self.check_interval)

        logger.info(f"Config watcher stopped for {self.config_path}")

    def start(self) -> None:
        """Start background thread to monitor configuration file.

        The watcher will check for file modifications every check_interval
        seconds and automatically reload the configuration when changes
        are detected.

        Safe to call multiple times - subsequent calls are ignored if
        watcher is already running.
        """
        if self._watcher_thread is not None and self._watcher_thread.is_alive():
            logger.debug("Config watcher already running")
            return

        self._stop_event.clear()
        self._watcher_thread = threading.Thread(
            target=self._watcher_loop,
            name=f"ConfigWatcher-{self.config_path.name}",
            daemon=True
        )
        self._watcher_thread.start()

    def stop(self) -> None:
        """Stop the background monitoring thread.

        Blocks until the watcher thread has fully stopped.
        Safe to call even if watcher is not running.
        """
        if self._watcher_thread is None or not self._watcher_thread.is_alive():
            return

        self._stop_event.set()
        self._watcher_thread.join(timeout=self.check_interval + 1.0)

        if self._watcher_thread.is_alive():
            logger.warning("Watcher thread did not stop cleanly")

    @property
    def current_config(self) -> HTTPClientConfig:
        """Get the currently active configuration.

        Thread-safe access to the most recently loaded configuration.

        Returns:
            Current HTTPClientConfig instance
        """
        with self._config_lock:
            if self._config is None:
                raise RuntimeError("Configuration not loaded")
            return self._config

    def reload_now(self) -> bool:
        """Force immediate configuration reload.

        Returns:
            True if reload succeeded, False if it failed
        """
        logger.info(f"Manual config reload requested for {self.config_path}")
        return self._load_config()


class ReloadableHTTPClient:
    """HTTPClient with automatic hot reload support.

    Wraps HTTPClient and automatically recreates it when the underlying
    configuration file changes. Useful for long-running processes that
    need to pick up configuration changes without restart.

    All HTTPClient methods are proxied through to the underlying client,
    which is automatically recreated when config changes.

    Example:
        >>> client = ReloadableHTTPClient("config.yaml", check_interval=10.0)
        >>> response = client.get("/api/data")  # Uses current config
        >>>
        >>> # Config file is modified...
        >>> # Next request uses updated config
        >>> response = client.get("/api/data")

    Example with context manager:
        >>> with ReloadableHTTPClient("config.yaml") as client:
        ...     while running:
        ...         client.get("/health")
        ...         time.sleep(60)
        # Watcher automatically stopped
    """

    def __init__(
        self,
        config_path: Union[str, Path],
        check_interval: float = 5.0,
    ):
        """Create HTTPClient with automatic config reload.

        Args:
            config_path: Path to configuration file (YAML or JSON)
            check_interval: Seconds between file modification checks

        Raises:
            FileNotFoundError: If config file doesn't exist
            ConfigValidationError: If initial config load fails
        """
        self.config_path = Path(config_path)
        self.check_interval = check_interval

        # Import here to avoid circular dependency
        from ..http_client import HTTPClient

        self._client_lock = threading.RLock()
        self._client: Optional[HTTPClient] = None

        # Create config watcher with reload callback
        self._watcher = ConfigWatcher(
            config_path=config_path,
            check_interval=check_interval,
            on_reload=self._on_config_reload,
        )

        # Create initial client
        self._recreate_client(self._watcher.current_config)

        # Start watching for changes
        self._watcher.start()

    def _on_config_reload(self, new_config: HTTPClientConfig) -> None:
        """Callback invoked when config is reloaded.

        Determines if client needs to be recreated based on what
        changed in the configuration.
        """
        logger.info("Configuration reloaded, recreating HTTPClient")
        self._recreate_client(new_config)

    def _recreate_client(self, config: HTTPClientConfig) -> None:
        """Create new HTTPClient instance with given config.

        Thread-safe recreation of the underlying client.
        """
        from ..http_client import HTTPClient

        with self._client_lock:
            # Close old client if exists
            if self._client is not None:
                try:
                    self._client.close()
                except Exception as e:
                    logger.warning(f"Error closing old client: {e}")

            # Create new client
            self._client = HTTPClient(config=config)

    @property
    def _current_client(self):
        """Get current HTTPClient instance (thread-safe)."""
        with self._client_lock:
            if self._client is None:
                raise RuntimeError("HTTPClient not initialized")
            return self._client

    # Proxy all HTTPClient methods

    def get(self, url: str, **kwargs):
        """Perform GET request with current config."""
        return self._current_client.get(url, **kwargs)

    def post(self, url: str, **kwargs):
        """Perform POST request with current config."""
        return self._current_client.post(url, **kwargs)

    def put(self, url: str, **kwargs):
        """Perform PUT request with current config."""
        return self._current_client.put(url, **kwargs)

    def patch(self, url: str, **kwargs):
        """Perform PATCH request with current config."""
        return self._current_client.patch(url, **kwargs)

    def delete(self, url: str, **kwargs):
        """Perform DELETE request with current config."""
        return self._current_client.delete(url, **kwargs)

    def head(self, url: str, **kwargs):
        """Perform HEAD request with current config."""
        return self._current_client.head(url, **kwargs)

    def options(self, url: str, **kwargs):
        """Perform OPTIONS request with current config."""
        return self._current_client.options(url, **kwargs)

    def request(self, method: str, url: str, **kwargs):
        """Perform HTTP request with current config."""
        return self._current_client.request(method, url, **kwargs)

    def download(self, url: str, output_path: str, **kwargs):
        """Download file with current config."""
        return self._current_client.download(url, output_path, **kwargs)

    def health_check(self, **kwargs):
        """Perform health check with current config."""
        return self._current_client.health_check(**kwargs)

    def add_plugin(self, plugin):
        """Add plugin to current client."""
        return self._current_client.add_plugin(plugin)

    def remove_plugin(self, plugin):
        """Remove plugin from current client."""
        return self._current_client.remove_plugin(plugin)

    @property
    def base_url(self):
        """Get base URL from current config."""
        return self._current_client.base_url

    @property
    def timeout(self):
        """Get timeout from current config."""
        return self._current_client.timeout

    @property
    def config(self):
        """Get current configuration."""
        return self._watcher.current_config

    def close(self) -> None:
        """Stop watcher and close client."""
        self._watcher.stop()
        with self._client_lock:
            if self._client is not None:
                self._client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stops watcher."""
        self.close()
        return False

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.close()
        except Exception:
            pass
