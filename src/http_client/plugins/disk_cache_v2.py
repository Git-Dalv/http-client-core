"""Disk cache plugin using PluginV2 API."""

import time
import hashlib
import json
from typing import Optional, Set
import requests
from diskcache import Cache

from .base_v2 import PluginV2
from ..core.context import RequestContext
from ..utils.serialization import serialize_response, deserialize_response


class DiskCachePluginV2(PluginV2):
    """Disk-based HTTP cache using diskcache library (v2 API).

    Features:
    - Persistent caching across sessions
    - TTL support
    - Method filtering (GET/HEAD only by default)
    - Size limiting
    - Cache statistics

    Example:
        >>> plugin = DiskCachePluginV2('/tmp/cache', ttl=3600)
        >>> client = HTTPClient(plugins=[plugin])
        >>>
        >>> # First request - cache miss
        >>> resp = client.get('https://api.example.com/users')
        >>>
        >>> # Second request - cache hit
        >>> resp = client.get('https://api.example.com/users')
        >>>
        >>> print(plugin.stats)
        {'hits': 1, 'misses': 1}
    """

    def __init__(
        self,
        cache_dir: str,
        ttl: int = 3600,
        max_size: Optional[int] = None,
        cacheable_methods: Optional[Set[str]] = None
    ):
        """Initialize disk cache plugin.

        Args:
            cache_dir: Directory to store cache files
            ttl: Time to live in seconds (default 1 hour)
            max_size: Maximum cache size in bytes (None = unlimited)
            cacheable_methods: HTTP methods to cache (default: GET, HEAD)
        """
        actual_size_limit = max_size if max_size is not None else 2**30  # 1 GB default
        self.cache = Cache(cache_dir, size_limit=actual_size_limit, eviction_policy="least-recently-used")
        self.cache_dir = cache_dir
        self.ttl = ttl
        self.max_size = max_size
        self.cacheable_methods = cacheable_methods or {'GET', 'HEAD'}
        self.stats = {'hits': 0, 'misses': 0}

    def before_request(self, ctx: RequestContext) -> Optional[requests.Response]:
        """Check cache before making request."""
        # Only cache specific methods
        if ctx.method.upper() not in self.cacheable_methods:
            return None

        # Generate cache key
        cache_key = self._generate_cache_key(ctx)
        ctx.metadata['cache_key'] = cache_key  # Store for after_response

        # Try to get from cache
        try:
            cached_data = self.cache.get(cache_key)

            if cached_data:
                # Check TTL
                age = time.time() - cached_data['timestamp']
                if age < self.ttl:
                    # Cache hit - deserialize and return
                    self.stats['hits'] += 1
                    response = deserialize_response(cached_data['response'])
                    response.headers['X-Cache'] = 'HIT'
                    return response
                else:
                    # Expired - remove
                    self.cache.delete(cache_key)

        except Exception as e:
            import logging
            logging.warning(f"Cache retrieval error: {e}")

        # Cache miss
        self.stats['misses'] += 1
        return None

    def after_response(self, ctx: RequestContext, response: requests.Response) -> requests.Response:
        """Save response to cache."""
        # Only cache specific methods
        if ctx.method.upper() not in self.cacheable_methods:
            return response

        # Only cache successful responses
        if response.status_code >= 400:
            return response

        # Check Cache-Control headers
        cache_control = response.headers.get("Cache-Control", "")
        if "no-store" in cache_control or "no-cache" in cache_control:
            return response

        try:
            # Get cache key from metadata (set in before_request)
            cache_key = ctx.metadata.get('cache_key')
            if not cache_key:
                cache_key = self._generate_cache_key(ctx)

            # Serialize and save
            cached_data = {
                'response': serialize_response(response),
                'timestamp': time.time()
            }

            self.cache.set(cache_key, cached_data)
            response.headers['X-Cache'] = 'MISS'

        except Exception as e:
            import logging
            logging.warning(f"Cache storage error: {e}")

        return response

    def _generate_cache_key(self, ctx: RequestContext) -> str:
        """Generate stable cache key from context."""
        params = ctx.kwargs.get('params', {})
        params_str = json.dumps(params, sort_keys=True) if params else ''

        key_source = f"{ctx.method}:{ctx.url}:{params_str}"
        return hashlib.sha256(key_source.encode('utf-8')).hexdigest()

    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()
        self.stats = {'hits': 0, 'misses': 0}

    def delete(self, ctx: RequestContext) -> bool:
        """Delete specific cache entry."""
        cache_key = self._generate_cache_key(ctx)
        return self.cache.delete(cache_key)

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": f"{hit_rate:.2f}%",
            "cache_size": len(self.cache),
            "disk_size_bytes": self.cache.volume(),
        }

    def close(self) -> None:
        """Close cache and release resources."""
        if hasattr(self, 'cache'):
            self.cache.close()

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"DiskCachePluginV2(cache_dir='{self.cache_dir}', ttl={self.ttl}, "
            f"hits={stats['hits']}, misses={stats['misses']}, "
            f"hit_rate={stats['hit_rate']})"
        )
