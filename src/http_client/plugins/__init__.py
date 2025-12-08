# src/http_client/plugins/__init__.py
from .auth_plugin import AuthPlugin
from .browser_fingerprint import BrowserFingerprintPlugin
from .cache_plugin import CachePlugin
from .disk_cache_plugin import DiskCachePlugin
from .logging_plugin import LoggingPlugin
from .monitoring_plugin import MonitoringPlugin
from .plugin import Plugin
from .rate_limit_plugin import RateLimitPlugin
from .retry_plugin import RetryPlugin
from .base_v2 import PluginV2
from .disk_cache_v2 import DiskCachePluginV2

# Async plugins
from .async_plugin import AsyncPlugin, SyncPluginAdapter
from .async_cache_plugin import AsyncCachePlugin
from .async_rate_limit_plugin import AsyncRateLimitPlugin
from .async_monitoring_plugin import AsyncMonitoringPlugin

__all__ = [
    # V1 API (legacy)
    "Plugin",
    "LoggingPlugin",
    "RetryPlugin",
    "CachePlugin",
    "RateLimitPlugin",
    "AuthPlugin",
    "DiskCachePlugin",
    "MonitoringPlugin",
    "BrowserFingerprintPlugin",
    # V2 API (recommended)
    "PluginV2",
    "DiskCachePluginV2",
    # Async plugins
    "AsyncPlugin",
    "SyncPluginAdapter",
    "AsyncCachePlugin",
    "AsyncRateLimitPlugin",
    "AsyncMonitoringPlugin",
]
