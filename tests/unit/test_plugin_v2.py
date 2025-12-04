"""Tests for PluginV2 API."""

import pytest
import requests
from typing import Optional

from src.http_client.core.context import RequestContext
from src.http_client.plugins.base_v2 import PluginV2
from src.http_client.plugins.disk_cache_v2 import DiskCachePluginV2


class TestRequestContext:
    """Test RequestContext dataclass."""

    def test_create_context(self):
        """Test creating request context."""
        ctx = RequestContext(
            method="GET",
            url="https://api.example.com/users"
        )

        assert ctx.method == "GET"
        assert ctx.url == "https://api.example.com/users"
        assert ctx.kwargs == {}
        assert ctx.metadata == {}
        assert ctx.request_id is not None

    def test_context_with_kwargs(self):
        """Test context with kwargs."""
        ctx = RequestContext(
            method="POST",
            url="https://api.example.com/users",
            kwargs={"json": {"name": "Alice"}, "headers": {"X-API-Key": "secret"}}
        )

        assert ctx.kwargs == {"json": {"name": "Alice"}, "headers": {"X-API-Key": "secret"}}

    def test_context_metadata(self):
        """Test context metadata for plugin communication."""
        ctx = RequestContext(method="GET", url="https://api.example.com/users")

        # Plugins can store data in metadata
        ctx.metadata['cache_key'] = 'abc123'
        ctx.metadata['user_id'] = 42

        assert ctx.metadata['cache_key'] == 'abc123'
        assert ctx.metadata['user_id'] == 42

    def test_context_copy(self):
        """Test copying context."""
        ctx = RequestContext(
            method="GET",
            url="https://api.example.com/users",
            kwargs={"params": {"page": 1}},
            request_id="test-123"
        )
        ctx.metadata['key'] = 'value'

        ctx_copy = ctx.copy()

        # Verify copy
        assert ctx_copy.method == ctx.method
        assert ctx_copy.url == ctx.url
        assert ctx_copy.request_id == ctx.request_id
        assert ctx_copy.kwargs == ctx.kwargs
        assert ctx_copy.metadata == ctx.metadata

        # Verify deep copy of kwargs
        ctx_copy.kwargs['params']['page'] = 2
        assert ctx.kwargs['params']['page'] == 1  # Original unchanged


class TestPluginV2:
    """Test PluginV2 base class."""

    def test_default_before_request(self):
        """Test default before_request returns None."""
        plugin = PluginV2()
        ctx = RequestContext(method="GET", url="https://api.example.com")

        result = plugin.before_request(ctx)
        assert result is None

    def test_default_after_response(self):
        """Test default after_response returns response unchanged."""
        plugin = PluginV2()
        ctx = RequestContext(method="GET", url="https://api.example.com")

        response = requests.Response()
        response.status_code = 200

        result = plugin.after_response(ctx, response)
        assert result is response

    def test_default_on_error(self):
        """Test default on_error returns False."""
        plugin = PluginV2()
        ctx = RequestContext(method="GET", url="https://api.example.com")

        result = plugin.on_error(ctx, Exception("test error"))
        assert result is False


class TestCustomPluginV2:
    """Test custom PluginV2 implementation."""

    def test_custom_plugin_short_circuit(self):
        """Test plugin can short-circuit request."""

        class BlockingPlugin(PluginV2):
            def __init__(self, blocked_urls):
                self.blocked_urls = blocked_urls

            def before_request(self, ctx: RequestContext) -> Optional[requests.Response]:
                if ctx.url in self.blocked_urls:
                    # Create blocked response
                    resp = requests.Response()
                    resp.status_code = 403
                    resp._content = b'Blocked'
                    return resp
                return None

        plugin = BlockingPlugin(['https://blocked.com'])
        ctx = RequestContext(method="GET", url="https://blocked.com")

        result = plugin.before_request(ctx)

        assert result is not None
        assert result.status_code == 403
        assert result.content == b'Blocked'

    def test_custom_plugin_modify_kwargs(self):
        """Test plugin can modify request kwargs."""

        class HeaderPlugin(PluginV2):
            def before_request(self, ctx: RequestContext) -> Optional[requests.Response]:
                # Add custom header
                if 'headers' not in ctx.kwargs:
                    ctx.kwargs['headers'] = {}
                ctx.kwargs['headers']['X-Custom'] = 'Value'
                return None

        plugin = HeaderPlugin()
        ctx = RequestContext(method="GET", url="https://api.example.com", kwargs={})

        plugin.before_request(ctx)

        assert ctx.kwargs['headers']['X-Custom'] == 'Value'

    def test_custom_plugin_metadata_communication(self):
        """Test plugins can communicate via metadata."""

        class MetadataPlugin1(PluginV2):
            def before_request(self, ctx: RequestContext):
                ctx.metadata['timestamp'] = 123456789
                return None

        class MetadataPlugin2(PluginV2):
            def after_response(self, ctx: RequestContext, response):
                # Can access data from Plugin1
                timestamp = ctx.metadata.get('timestamp')
                response.headers['X-Request-Time'] = str(timestamp)
                return response

        ctx = RequestContext(method="GET", url="https://api.example.com")

        # Plugin 1 sets metadata
        plugin1 = MetadataPlugin1()
        plugin1.before_request(ctx)

        # Plugin 2 reads metadata
        plugin2 = MetadataPlugin2()
        response = requests.Response()
        response.headers = {}
        result = plugin2.after_response(ctx, response)

        assert result.headers['X-Request-Time'] == '123456789'


class TestDiskCachePluginV2:
    """Test DiskCachePluginV2."""

    def test_create_plugin(self, tmp_path):
        """Test creating disk cache plugin."""
        cache_dir = str(tmp_path / "cache")
        plugin = DiskCachePluginV2(cache_dir, ttl=3600)

        assert plugin.cache_dir == cache_dir
        assert plugin.ttl == 3600
        assert plugin.cacheable_methods == {'GET', 'HEAD'}
        assert plugin.stats == {'hits': 0, 'misses': 0}

        plugin.close()

    def test_cache_key_generation(self, tmp_path):
        """Test cache key generation."""
        cache_dir = str(tmp_path / "cache")
        plugin = DiskCachePluginV2(cache_dir)

        try:
            ctx1 = RequestContext(method="GET", url="https://api.example.com/users")
            ctx2 = RequestContext(method="GET", url="https://api.example.com/users")
            ctx3 = RequestContext(method="GET", url="https://api.example.com/posts")

            key1 = plugin._generate_cache_key(ctx1)
            key2 = plugin._generate_cache_key(ctx2)
            key3 = plugin._generate_cache_key(ctx3)

            # Same context = same key
            assert key1 == key2

            # Different URL = different key
            assert key1 != key3
        finally:
            plugin.close()

    def test_cache_stats(self, tmp_path):
        """Test cache statistics."""
        cache_dir = str(tmp_path / "cache")
        plugin = DiskCachePluginV2(cache_dir)

        try:
            stats = plugin.get_stats()

            assert stats['hits'] == 0
            assert stats['misses'] == 0
            assert 'hit_rate' in stats
            assert stats['cache_size'] == 0
        finally:
            plugin.close()

    def test_repr(self, tmp_path):
        """Test string representation."""
        cache_dir = str(tmp_path / "cache")
        plugin = DiskCachePluginV2(cache_dir, ttl=7200)

        try:
            repr_str = repr(plugin)

            assert "DiskCachePluginV2" in repr_str
            assert cache_dir in repr_str
            assert "ttl=7200" in repr_str
        finally:
            plugin.close()
