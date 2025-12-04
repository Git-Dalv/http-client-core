# Migration Guide: Plugin API v1 → v2

## Overview

Version 2.0 introduces a new plugin API with `RequestContext` for better
plugin communication and cleaner architecture.

## Key Changes

### Old API (v1)
```python
class MyPlugin(Plugin):
    def before_request(self, method, url, **kwargs):
        # No access to full context
        # Cannot return Response directly
        return kwargs

    def after_response(self, response):
        # No access to request parameters
        # Must use thread-local hacks
        return response
```

### New API (v2)
```python
class MyPlugin(PluginV2):
    def before_request(self, ctx: RequestContext) -> Optional[Response]:
        # Full context available
        # Can return Response to short-circuit
        return None

    def after_response(self, ctx: RequestContext, response: Response):
        # Full context available
        # Can access request parameters
        return response
```

## Migration Steps

### Step 1: Change base class
```python
# Old
from http_client.plugins import Plugin

class MyPlugin(Plugin):
    pass

# New
from http_client.plugins import PluginV2

class MyPlugin(PluginV2):
    pass
```

### Step 2: Update before_request signature
```python
# Old
def before_request(self, method: str, url: str, **kwargs) -> Dict:
    cache_key = f"{method}:{url}"
    # Store in instance variable for later
    self._last_key = cache_key
    return kwargs

# New
def before_request(self, ctx: RequestContext) -> Optional[Response]:
    cache_key = f"{ctx.method}:{ctx.url}"
    # Store in context metadata
    ctx.metadata['cache_key'] = cache_key

    # Can return Response directly
    if self.has_cache(cache_key):
        return self.get_cached(cache_key)

    return None
```

### Step 3: Update after_response signature
```python
# Old
def after_response(self, response: Response) -> Response:
    # Need to retrieve request info from instance variable
    cache_key = self._last_key
    self.save_cache(cache_key, response)
    return response

# New
def after_response(self, ctx: RequestContext, response: Response) -> Response:
    # Context has all request info
    cache_key = ctx.metadata.get('cache_key')
    self.save_cache(cache_key, response)
    return response
```

## Benefits of v2 API

### 1. **No More State Management Hacks**
```python
# V1 - Must store state in instance variables (not thread-safe!)
class MyPluginV1(Plugin):
    def before_request(self, method, url, **kwargs):
        self._current_url = url  # Thread-unsafe!
        return kwargs

    def after_response(self, response):
        url = self._current_url  # Hope it's still correct...
        return response

# V2 - Context provides all info
class MyPluginV2(PluginV2):
    def after_response(self, ctx, response):
        url = ctx.url  # Always correct!
        return response
```

### 2. **Better Plugin Communication**
```python
# V2 - Plugins can share data via metadata
class Plugin1(PluginV2):
    def before_request(self, ctx):
        ctx.metadata['user_id'] = self.get_user_id()
        return None

class Plugin2(PluginV2):
    def after_response(self, ctx, response):
        user_id = ctx.metadata.get('user_id')
        self.log_for_user(user_id, response)
        return response
```

### 3. **Cleaner Short-Circuiting**
```python
# V1 - Use magic key hack
def before_request(self, method, url, **kwargs):
    if cached := self.get_cache(url):
        return {'__cached_response__': cached}  # Awkward!
    return kwargs

# V2 - Return Response directly
def before_request(self, ctx):
    if cached := self.get_cache(ctx.url):
        return cached  # Clean!
    return None
```

## Backward Compatibility

HTTPClient v2.x supports **both** v1 and v2 plugins simultaneously:
```python
from http_client import HTTPClient
from http_client.plugins import RetryPlugin  # v1
from http_client.plugins import DiskCachePluginV2  # v2

client = HTTPClient(plugins=[
    RetryPlugin(),  # v1 plugin - still works
    DiskCachePluginV2('/tmp/cache')  # v2 plugin
])
```

## Timeline

- **v1.x**: v1 API only
- **v2.0-2.x**: Both APIs supported, v1 deprecated
- **v3.0**: v1 API removed

## Example: DiskCachePlugin Migration

### Before (v1)
```python
class DiskCachePlugin(Plugin):
    def before_request(self, method, url, **kwargs):
        if method.upper() not in self.cacheable_methods:
            return {}

        cache_key = self._generate_cache_key(method, url, kwargs)
        cached_data = self.cache.get(cache_key)

        if cached_data:
            self.stats["hits"] += 1
            cached_response = deserialize_response(cached_data)
            return {"__cached_response__": cached_response}

        self.stats["misses"] += 1
        return {}

    def after_response(self, response):
        # Need to use thread-local storage hack!
        from ..core.http_client import get_current_request_context
        context = get_current_request_context()

        if not context:
            return response

        method = context.get("method")
        url = context.get("url")
        kwargs = context.get("kwargs", {})

        if self._should_cache(method, response):
            cache_key = self._generate_cache_key(method, url, kwargs)
            serialized = serialize_response(response)
            self.cache.set(cache_key, serialized, expire=self.ttl)

        return response
```

### After (v2)
```python
class DiskCachePluginV2(PluginV2):
    def before_request(self, ctx: RequestContext) -> Optional[Response]:
        if ctx.method.upper() not in self.cacheable_methods:
            return None

        cache_key = self._generate_cache_key(ctx)
        ctx.metadata['cache_key'] = cache_key

        cached_data = self.cache.get(cache_key)
        if cached_data:
            self.stats["hits"] += 1
            return deserialize_response(cached_data)

        self.stats["misses"] += 1
        return None

    def after_response(self, ctx: RequestContext, response: Response) -> Response:
        # Context has all info - no hacks needed!
        if ctx.method.upper() not in self.cacheable_methods:
            return response

        if response.status_code >= 400:
            return response

        cache_key = ctx.metadata.get('cache_key')
        if not cache_key:
            cache_key = self._generate_cache_key(ctx)

        cached_data = {
            'response': serialize_response(response),
            'timestamp': time.time()
        }
        self.cache.set(cache_key, cached_data)

        return response
```

## Full Example Code

See `src/http_client/plugins/disk_cache_v2.py` for a complete working example.

## FAQ

**Q: Do I need to migrate all my plugins immediately?**
A: No! v1 plugins continue to work in v2.x. Migrate at your own pace.

**Q: Can I mix v1 and v2 plugins?**
A: Yes! HTTPClient detects the API version automatically.

**Q: What if I need backward compatibility?**
A: Provide both v1 and v2 versions of your plugin as separate classes.

**Q: When will v1 be removed?**
A: Not before v3.0 (at least 1 year away). You'll have plenty of time to migrate.

## Help

If you have questions about migration, please:
- Check the examples in `src/http_client/plugins/disk_cache_v2.py`
- Open an issue on GitHub
- Ask in the community forum
