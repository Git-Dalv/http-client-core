# Migration Guide: v1.x to v2.0

This guide helps you migrate from HTTP Client Core v1.x to v2.0.

## Overview

Version 2.0 removes deprecated APIs and introduces breaking changes for cleaner, more maintainable code. Most changes involve moving from constructor parameters to structured configuration objects.

## Quick Migration Checklist

- [ ] Replace deprecated constructor parameters with `HTTPClientConfig`
- [ ] Update exception handling for new hierarchy
- [ ] Review retry behavior for POST requests
- [ ] Update plugin registration if using deprecated methods
- [ ] Run migration checker tool

## Migration Checker Tool

Run the built-in migration checker to find deprecated usage:

```bash
python -m http_client.tools.migration_check /path/to/your/code
```

Or enable strict mode to treat deprecation warnings as errors:

```bash
export HTTP_CLIENT_STRICT_DEPRECATION=1
python your_app.py
```

## Deprecated Parameters

### Constructor Parameters

| v1.x (Deprecated) | v2.0 (Use Instead) |
|-------------------|-------------------|
| `max_retries=5` | `config.retry.max_attempts=5` |
| `verify_ssl=False` | `config.security.verify_ssl=False` |
| `pool_connections=20` | `config.pool.pool_connections=20` |
| `pool_maxsize=20` | `config.pool.pool_maxsize=20` |
| `max_redirects=10` | `config.pool.max_redirects=10` |
| `pool_block=True` | `config.pool.pool_block=True` |

### Before (v1.x)

```python
from http_client import HTTPClient

# ❌ Deprecated - will be removed in v2.0
client = HTTPClient(
    base_url="https://api.example.com",
    max_retries=5,
    verify_ssl=True,
    pool_connections=20,
    pool_maxsize=20,
    max_redirects=10,
)
```

### After (v2.0)

```python
from http_client import (
    HTTPClient,
    HTTPClientConfig,
    RetryConfig,
    SecurityConfig,
    ConnectionPoolConfig,
)

# ✅ Recommended - explicit configuration
config = HTTPClientConfig(
    base_url="https://api.example.com",
    retry=RetryConfig(max_attempts=5),
    security=SecurityConfig(verify_ssl=True),
    pool=ConnectionPoolConfig(
        pool_connections=20,
        pool_maxsize=20,
        max_redirects=10,
    ),
)

client = HTTPClient(config=config)
```

### Quick Migration with Factory Method

```python
from http_client import HTTPClientConfig, HTTPClient

# ✅ Quick migration using factory method
config = HTTPClientConfig.create(
    base_url="https://api.example.com",
    timeout=30,
    max_retries=5,
    verify_ssl=True,
)

client = HTTPClient(config=config)
```

## Exception Handling Changes

### New Exception Hierarchy

```
HTTPClientException
├── TemporaryError (retryable=True)
│   ├── NetworkError
│   │   ├── TimeoutError
│   │   ├── ConnectionError
│   │   ├── ProxyError
│   │   └── DNSError
│   ├── ServerError (5xx)
│   └── TooManyRequestsError (429)
└── FatalError (fatal=True, not retryable)
    ├── HTTPError (4xx except 429)
    │   ├── BadRequestError (400)
    │   ├── UnauthorizedError (401)
    │   ├── ForbiddenError (403)
    │   └── NotFoundError (404)
    ├── InvalidResponseError
    ├── ResponseTooLargeError
    ├── DecompressionBombError
    └── CircuitOpenError
```

### Before (v1.x)

```python
from http_client import HTTPClient, HTTPError

try:
    response = client.get("/api/data")
except HTTPError:
    # Caught both 4xx and 5xx
    pass
```

### After (v2.0)

```python
from http_client import (
    HTTPClient,
    ServerError,      # 5xx - retryable
    HTTPError,        # 4xx - not retryable
    TimeoutError,
    ConnectionError,
    TooManyRetriesError,
)

try:
    response = client.get("/api/data")
except ServerError as e:
    # 5xx errors (automatically retried)
    print(f"Server error: {e.status_code}")
except HTTPError as e:
    # 4xx errors (not retried)
    print(f"Client error: {e.status_code}")
except TimeoutError:
    # Timeout (automatically retried for GET)
    print("Request timed out")
except TooManyRetriesError as e:
    # Max retries exceeded
    print(f"Failed after {e.max_retries} retries")
```

## Retry Behavior Changes

### POST Requests No Longer Retry by Default

In v1.x, all requests were retried. In v2.0, only idempotent methods (GET, HEAD, OPTIONS, PUT, DELETE) are retried by default.

```python
from http_client import HTTPClientConfig, RetryConfig

# To enable POST retry (use with caution!)
config = HTTPClientConfig(
    retry=RetryConfig(
        max_attempts=3,
        idempotent_methods={"GET", "HEAD", "OPTIONS", "PUT", "DELETE", "POST"},
    ),
)
```

## Configuration Immutability

`HTTPClientConfig` and all sub-configs are now immutable (frozen dataclasses). To modify configuration, create a new instance:

### Before (v1.x)

```python
# ❌ This will raise an error in v2.0
client = HTTPClient(base_url="https://api.example.com")
client._timeout = 60  # Direct modification
```

### After (v2.0)

```python
# ✅ Create new config with modifications
config = HTTPClientConfig(base_url="https://api.example.com")
new_config = config.with_timeout(60)
new_client = HTTPClient(config=new_config)

# Or use helper methods
config = HTTPClientConfig.create(base_url="https://api.example.com")
config = config.with_headers({"X-API-Key": "secret"})
config = config.with_retries(5)
```

## Plugin Changes

### LoggingPlugin Deprecated

The `LoggingPlugin` is deprecated in favor of built-in logging configuration:

### Before (v1.x)

```python
from http_client import HTTPClient, LoggingPlugin

client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(LoggingPlugin(level="DEBUG"))
```

### After (v2.0)

```python
from http_client import HTTPClient, HTTPClientConfig
from http_client.core.config import LoggingConfig

config = HTTPClientConfig(
    base_url="https://api.example.com",
    logging=LoggingConfig(
        level="DEBUG",
        format="json",
        enable_console=True,
    ),
)

client = HTTPClient(config=config)
```

### Plugin Priority

Plugins now have explicit priorities. Ensure your custom plugins set appropriate priority:

```python
from http_client.plugins import Plugin, PluginPriority

class MyPlugin(Plugin):
    priority = PluginPriority.NORMAL  # 50
    
    # Or use numeric value
    priority = 25  # Higher priority (runs earlier)
```

## New Features to Consider

### Circuit Breaker

Protect against cascading failures:

```python
from http_client import HTTPClientConfig, CircuitBreakerConfig

config = HTTPClientConfig(
    base_url="https://api.example.com",
    circuit_breaker=CircuitBreakerConfig(
        enabled=True,
        failure_threshold=5,
        recovery_timeout=30.0,
    ),
)
```

### Async Client

For async applications:

```python
from http_client import AsyncHTTPClient

async with AsyncHTTPClient(base_url="https://api.example.com") as client:
    response = await client.get("/users")
```

### Health Checks

Monitor client health:

```python
health = client.health_check(test_url="https://api.example.com/health")
print(f"Healthy: {health['healthy']}")
```

## Testing Migration

1. Run migration checker:
   ```bash
   python -m http_client.tools.migration_check ./src
   ```

2. Enable strict mode in tests:
   ```python
   import os
   os.environ["HTTP_CLIENT_STRICT_DEPRECATION"] = "1"
   ```

3. Run your test suite and fix any errors

4. Remove strict mode environment variable

## Getting Help

- **Issues**: https://github.com/Git-Dalv/http-client-core/issues
- **Discussions**: https://github.com/Git-Dalv/http-client-core/discussions
- **Documentation**: https://github.com/Git-Dalv/http-client-core#readme
