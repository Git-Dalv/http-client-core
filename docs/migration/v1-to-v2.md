# Migration Guide: v1.x to v2.0

## Overview

Version 2.0 introduces a unified configuration system and removes deprecated plugins. This guide helps you migrate your code from v1.x to v2.0.

**Timeline:**
- **v1.5.0**: Deprecation warnings added (current version)
- **v1.9.0**: Warnings become errors in strict mode
- **v2.0.0**: Deprecated APIs removed (breaking changes)

## Quick Migration Checklist

- [ ] Replace `LoggingPlugin` with `HTTPClientConfig.logging`
- [ ] Replace deprecated constructor parameters with config objects
- [ ] Update `RetryPlugin` usage to built-in retry system
- [ ] Test with `HTTP_CLIENT_STRICT_DEPRECATION=1` environment variable
- [ ] Run migration checker: `python -m http_client.tools.migration_check`

## Breaking Changes

### 1. LoggingPlugin Removed

The `LoggingPlugin` is deprecated and will be removed in v2.0.0. Use the built-in logging configuration instead.

**Before (v1.x - Deprecated):**

```python
from http_client import HTTPClient
from http_client.plugins import LoggingPlugin

client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(LoggingPlugin(level="DEBUG"))

# Make requests
response = client.get("/users")
```

**After (v2.0 - Recommended):**

```python
from http_client import HTTPClient
from http_client.core.config import HTTPClientConfig, LoggingConfig

config = HTTPClientConfig.create(
    base_url="https://api.example.com",
    logging=LoggingConfig.create(
        level="DEBUG",
        format="json",  # or "text"
        enable_request_logging=True,
        enable_response_logging=True
    )
)
client = HTTPClient(config=config)

# Make requests
response = client.get("/users")
```

**Benefits of new approach:**
- More consistent configuration
- Better type hints and IDE support
- Configuration can be loaded from files (YAML/JSON)
- Hot reload support for long-running processes

### 2. Deprecated Constructor Parameters

Several HTTPClient constructor parameters are deprecated in favor of structured config objects.

#### Full Mapping Table

| Old Parameter | New Location | Config Class | Example |
|--------------|--------------|--------------|---------|
| `max_retries` | `config.retry.max_attempts` | `RetryConfig` | `RetryConfig(max_attempts=3)` |
| `pool_connections` | `config.pool.pool_connections` | `ConnectionPoolConfig` | `ConnectionPoolConfig(pool_connections=10)` |
| `pool_maxsize` | `config.pool.pool_maxsize` | `ConnectionPoolConfig` | `ConnectionPoolConfig(pool_maxsize=10)` |
| `max_redirects` | `config.pool.max_redirects` | `ConnectionPoolConfig` | `ConnectionPoolConfig(max_redirects=5)` |
| `verify_ssl` | `config.security.verify_ssl` | `SecurityConfig` | `SecurityConfig(verify_ssl=True)` |

#### Example: Multiple Parameters

**Before (v1.x - Deprecated):**

```python
from http_client import HTTPClient

client = HTTPClient(
    base_url="https://api.example.com",
    max_retries=5,
    pool_connections=20,
    pool_maxsize=20,
    max_redirects=10,
    verify_ssl=False,
    timeout=30
)
```

**After (v2.0 - Recommended):**

```python
from http_client import HTTPClient
from http_client.core.config import (
    HTTPClientConfig,
    RetryConfig,
    ConnectionPoolConfig,
    SecurityConfig,
    TimeoutConfig
)

config = HTTPClientConfig.create(
    base_url="https://api.example.com",
    retry=RetryConfig(max_attempts=5),
    pool=ConnectionPoolConfig(
        pool_connections=20,
        pool_maxsize=20,
        max_redirects=10
    ),
    security=SecurityConfig(verify_ssl=False),
    timeout=TimeoutConfig(read=30)
)
client = HTTPClient(config=config)
```

**Shortcut (v1.5+ compatibility layer):**

For simpler cases, you can still use shortcuts that will be converted internally:

```python
config = HTTPClientConfig.create(
    base_url="https://api.example.com",
    max_retries=5,  # Shortcut still works
    timeout=30       # Shortcut still works
)
client = HTTPClient(config=config)
```

### 3. RetryPlugin Replaced with Built-in System

The `RetryPlugin` is deprecated because retry functionality is now built into HTTPClient.

**Before (v1.x - Deprecated):**

```python
from http_client import HTTPClient
from http_client.plugins import RetryPlugin

retry = RetryPlugin(max_retries=3, backoff_factor=0.5)
client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(retry)
```

**After (v2.0 - Recommended):**

```python
from http_client import HTTPClient
from http_client.core.config import HTTPClientConfig, RetryConfig

config = HTTPClientConfig.create(
    base_url="https://api.example.com",
    retry=RetryConfig(
        max_attempts=3,
        backoff_factor=0.5,
        backoff_base=0.5,
        backoff_jitter=True,
        respect_retry_after=True
    )
)
client = HTTPClient(config=config)
```

**Note:** The built-in retry system is more powerful and supports:
- Exponential backoff with jitter
- Respect for `Retry-After` headers
- Per-method retry configuration
- Status code-based retry rules

### 4. Configuration from Files

**New in v1.5+**: Load configuration from YAML or JSON files.

**config.yaml:**

```yaml
http_client:
  base_url: "https://api.example.com"

  timeout:
    connect: 5
    read: 30

  retry:
    max_attempts: 3
    backoff_factor: 2.0
    backoff_jitter: true

  pool:
    pool_connections: 10
    pool_maxsize: 10

  security:
    verify_ssl: true

  logging:
    level: "INFO"
    format: "json"
```

**Python code:**

```python
from http_client import HTTPClient
from http_client.core.env_config import ConfigFileLoader

# Load config from file
config = ConfigFileLoader.from_yaml("config.yaml")
client = HTTPClient(config=config)
```

### 5. Hot Reload for Long-Running Processes

**New in v1.5+**: Automatically reload configuration when file changes.

**Before (v1.x):**

```python
# Required application restart to update config
client = HTTPClient(base_url="https://api.example.com", timeout=30)
```

**After (v1.5+):**

```python
from http_client import ReloadableHTTPClient

# Config reloads automatically every 10 seconds
client = ReloadableHTTPClient("config.yaml", check_interval=10.0)

# Always uses latest configuration
response = client.get("/api/data")
```

## Migration Strategies

### Strategy 1: Gradual Migration (Recommended)

1. **Update imports** but keep using deprecated APIs
2. **Fix deprecation warnings** one by one
3. **Test thoroughly** after each change
4. **Enable strict mode** to catch remaining issues

```bash
# Run with strict mode to find all deprecated usage
HTTP_CLIENT_STRICT_DEPRECATION=1 python -m pytest tests/
```

### Strategy 2: Automated Migration

Use the migration checker tool to find all deprecated usage:

```bash
# Check single file
python -m http_client.tools.migration_check your_code.py

# Check entire project
python -m http_client.tools.migration_check src/ --recursive

# Generate migration report
python -m http_client.tools.migration_check src/ --recursive --output report.txt
```

The tool will output:

```
Checking: src/app.py
  Line 15: LoggingPlugin import - Use HTTPClientConfig.logging instead
  Line 42: Parameter 'max_retries' - Use config.retry.max_attempts
  Line 42: Parameter 'verify_ssl' - Use config.security.verify_ssl

Found 3 issues in 1 file.
See migration guide: https://github.com/Git-Dalv/http-client-core/blob/main/docs/migration/v1-to-v2.md
```

### Strategy 3: Side-by-Side Comparison

Create new v2 code alongside old v1 code:

```python
# old_client.py (v1.x)
from http_client import HTTPClient
from http_client.plugins import LoggingPlugin

def create_client_v1():
    client = HTTPClient(base_url="https://api.example.com", max_retries=3)
    client.add_plugin(LoggingPlugin(level="DEBUG"))
    return client

# new_client.py (v2.0)
from http_client import HTTPClient
from http_client.core.config import HTTPClientConfig, RetryConfig, LoggingConfig

def create_client_v2():
    config = HTTPClientConfig.create(
        base_url="https://api.example.com",
        retry=RetryConfig(max_attempts=3),
        logging=LoggingConfig.create(level="DEBUG")
    )
    return HTTPClient(config=config)
```

## Common Migration Patterns

### Pattern 1: Basic Client with Retry

**Before:**

```python
client = HTTPClient(
    base_url="https://api.example.com",
    max_retries=3,
    timeout=30
)
```

**After:**

```python
config = HTTPClientConfig.create(
    base_url="https://api.example.com",
    retry=RetryConfig(max_attempts=3),
    timeout=TimeoutConfig(read=30)
)
client = HTTPClient(config=config)
```

### Pattern 2: Client with Custom Pool Settings

**Before:**

```python
client = HTTPClient(
    base_url="https://api.example.com",
    pool_connections=20,
    pool_maxsize=20,
    max_redirects=5
)
```

**After:**

```python
config = HTTPClientConfig.create(
    base_url="https://api.example.com",
    pool=ConnectionPoolConfig(
        pool_connections=20,
        pool_maxsize=20,
        max_redirects=5
    )
)
client = HTTPClient(config=config)
```

### Pattern 3: Client with Logging

**Before:**

```python
client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(LoggingPlugin(level="DEBUG"))
```

**After:**

```python
config = HTTPClientConfig.create(
    base_url="https://api.example.com",
    logging=LoggingConfig.create(
        level="DEBUG",
        format="json"
    )
)
client = HTTPClient(config=config)
```

### Pattern 4: Multiple Plugins

**Before:**

```python
from http_client import HTTPClient
from http_client.plugins import (
    LoggingPlugin,
    MonitoringPlugin,
    RateLimitPlugin
)

client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(LoggingPlugin(level="INFO"))
client.add_plugin(MonitoringPlugin())
client.add_plugin(RateLimitPlugin(max_requests_per_second=10))
```

**After:**

```python
from http_client import HTTPClient
from http_client.core.config import HTTPClientConfig, LoggingConfig
from http_client.plugins import MonitoringPlugin, RateLimitPlugin

config = HTTPClientConfig.create(
    base_url="https://api.example.com",
    logging=LoggingConfig.create(level="INFO")
)
client = HTTPClient(config=config)

# Non-deprecated plugins still work
client.add_plugin(MonitoringPlugin())
client.add_plugin(RateLimitPlugin(max_requests_per_second=10))
```

## Testing Your Migration

### 1. Run Tests with Strict Mode

Enable strict deprecation mode to convert warnings into errors:

```bash
# Will fail if any deprecated APIs are used
HTTP_CLIENT_STRICT_DEPRECATION=1 pytest tests/
```

### 2. Use Migration Checker

```bash
# Check your codebase
python -m http_client.tools.migration_check src/ --recursive

# Exit code 0 = no issues
# Exit code 1 = deprecated usage found
```

### 3. Gradual Rollout

1. **Development**: Migrate and test locally
2. **Staging**: Deploy to staging environment
3. **Canary**: Deploy to small % of production traffic
4. **Production**: Full rollout

## Troubleshooting

### Issue: "module 'http_client.plugins' has no attribute 'LoggingPlugin'"

**Cause:** Running code with v2.0.0 that still uses deprecated `LoggingPlugin`.

**Solution:** Migrate to `HTTPClientConfig.logging`:

```python
# Remove this:
from http_client.plugins import LoggingPlugin
client.add_plugin(LoggingPlugin(level="DEBUG"))

# Use this:
from http_client.core.config import LoggingConfig
config = HTTPClientConfig.create(
    base_url="...",
    logging=LoggingConfig.create(level="DEBUG")
)
```

### Issue: "TypeError: __init__() got an unexpected keyword argument 'max_retries'"

**Cause:** Running code with v2.0.0 that uses deprecated constructor parameters.

**Solution:** Use config objects:

```python
# Remove this:
client = HTTPClient(base_url="...", max_retries=3)

# Use this:
config = HTTPClientConfig.create(
    base_url="...",
    retry=RetryConfig(max_attempts=3)
)
client = HTTPClient(config=config)
```

### Issue: Deprecation warnings in tests

**Temporary workaround:** Suppress warnings during migration:

```python
import warnings

# In test setup
warnings.filterwarnings("ignore", category=DeprecationWarning, module="http_client")
```

**Long-term solution:** Fix the deprecated usage.

## FAQ

### Q: When will v2.0.0 be released?

A: V2.0.0 release is planned for Q2 2025. Exact date TBD.

### Q: Can I use v1.x and v2.0 APIs together?

A: Yes, during the migration period (v1.5 - v1.9), both old and new APIs work. However, deprecated APIs will be removed in v2.0.0.

### Q: Will my existing code break immediately?

A: No. Deprecated APIs still work in v1.x but emit warnings. They will be removed in v2.0.0.

### Q: How long will v1.x be supported?

A: V1.x will receive security updates for 6 months after v2.0.0 release.

### Q: Is there an automatic migration tool?

A: Yes, use `python -m http_client.tools.migration_check` to find deprecated usage. However, you'll need to update the code manually.

### Q: Can I opt-out of deprecation warnings?

A: Not recommended, but you can filter warnings:

```python
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="http_client")
```

## Getting Help

- **Documentation**: https://github.com/Git-Dalv/http-client-core/tree/main/docs
- **Migration Guide**: https://github.com/Git-Dalv/http-client-core/blob/main/docs/migration/v1-to-v2.md
- **Issues**: https://github.com/Git-Dalv/http-client-core/issues
- **Discussions**: https://github.com/Git-Dalv/http-client-core/discussions

## Summary

**Key Actions:**
1. ✅ Replace `LoggingPlugin` with `HTTPClientConfig.logging`
2. ✅ Replace deprecated constructor params with config objects
3. ✅ Use `RetryConfig` instead of `RetryPlugin`
4. ✅ Consider using config files (YAML/JSON) for easier management
5. ✅ Test with `HTTP_CLIENT_STRICT_DEPRECATION=1`
6. ✅ Run migration checker tool

**Benefits of v2.0:**
- Cleaner, more consistent API
- Better type safety and IDE support
- Configuration from files (YAML/JSON)
- Hot reload for long-running processes
- Improved documentation and examples

**Need help?** Open an issue or start a discussion on GitHub!
