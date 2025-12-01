# Migration Guide: v0.x → v1.0

## Overview

Version 1.0 introduces a new configuration system for better type safety and immutability.

## Breaking Changes

### 1. Configuration System

**Before (v0.x):**
```python
client = HTTPClient(
    base_url="https://api.example.com",
    timeout=30,
    max_retries=3,
    verify_ssl=True
)
```

**After (v1.0):**
```python
# Option 1: Simple (backward compatible, shows deprecation warnings)
client = HTTPClient(
    base_url="https://api.example.com",
    timeout=30,
    max_retries=3  # Shows deprecation warning
)

# Option 2: Explicit config (recommended)
from src.http_client import HTTPClientConfig

config = HTTPClientConfig.create(
    base_url="https://api.example.com",
    timeout=30,
    max_retries=3
)
client = HTTPClient(config=config)

# Option 3: Advanced config
from src.http_client import (
    HTTPClientConfig,
    TimeoutConfig,
    RetryConfig,
)

config = HTTPClientConfig(
    base_url="https://api.example.com",
    timeout=TimeoutConfig(connect=5, read=30),
    retry=RetryConfig(max_attempts=3, backoff_factor=2.0)
)
client = HTTPClient(config=config)
```

### 2. Immutability

**Before (v0.x):**
```python
client = HTTPClient(base_url="https://api.example.com")
client.timeout = 60  # Could modify after creation
```

**After (v1.0):**
```python
client = HTTPClient(base_url="https://api.example.com")
client.timeout = 60  # ❌ Raises RuntimeError

# Create new client instead:
new_client = HTTPClient(
    base_url="https://api.example.com",
    timeout=60
)
```

### 3. Retry Behavior

**Changes:**
- POST requests are NO LONGER retried by default (non-idempotent)
- Only idempotent methods retry: GET, HEAD, PUT, DELETE, OPTIONS, TRACE
- Retry-After header is now respected

**Before (v0.x):**
```python
# POST was retried
client.post("/api/data", json={"test": "data"})  # Would retry on 500
```

**After (v1.0):**
```python
# POST is NOT retried by default
client.post("/api/data", json={"test": "data"})  # No retry on 500

# To force retry on POST (not recommended):
from src.http_client import HTTPClientConfig, RetryConfig

retry_cfg = RetryConfig(
    max_attempts=3,
    idempotent_methods={'GET', 'HEAD', 'PUT', 'DELETE', 'OPTIONS', 'TRACE', 'POST'}
)
config = HTTPClientConfig(base_url="...", retry=retry_cfg)
client = HTTPClient(config=config)
```

### 4. Exception Hierarchy

**New exception structure:**
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
    └── DecompressionBombError
```

**Before (v0.x):**
```python
try:
    response = client.get("/api/data")
except HTTPError:
    # Caught both 4xx and 5xx
    pass
```

**After (v1.0):**
```python
from src.http_client import ServerError, HTTPError

try:
    response = client.get("/api/data")
except ServerError:
    # Only 5xx errors (retryable)
    pass
except HTTPError:
    # Only 4xx errors (fatal)
    pass
```

## Deprecation Timeline

| Feature | Deprecated In | Removed In | Alternative |
|---------|--------------|------------|-------------|
| `max_retries` parameter | 1.0.0 | 2.0.0 | `config.retry.max_attempts` |
| `verify_ssl` parameter | 1.0.0 | 2.0.0 | `config.security.verify_ssl` |
| `max_redirects` parameter | 1.0.0 | 2.0.0 | `config.pool.max_redirects` |
| `pool_connections` parameter | 1.0.0 | 2.0.0 | `config.pool.pool_connections` |
| `pool_maxsize` parameter | 1.0.0 | 2.0.0 | `config.pool.pool_maxsize` |
| Direct attribute modification | 1.0.0 | 2.0.0 | Create new instance |

## New Features in v1.0

### 1. Security Features
```python
# Response size limits
config = HTTPClientConfig.create(
    base_url="...",
)
# Default: max_response_size = 100MB
# Default: max_decompressed_size = 500MB

# Custom limits:
from src.http_client import SecurityConfig

security = SecurityConfig(
    max_response_size=50 * 1024 * 1024,  # 50MB
    max_decompressed_size=200 * 1024 * 1024  # 200MB
)
config = HTTPClientConfig(base_url="...", security=security)
```

### 2. Stream Downloads
```python
# Download large files without loading into memory
client = HTTPClient(base_url="https://example.com")
bytes_downloaded = client.download(
    "/large-file.zip",
    "output.zip",
    chunk_size=8192,
    show_progress=True  # Requires tqdm
)
print(f"Downloaded {bytes_downloaded} bytes")
```

### 3. Correlation ID
```python
# Automatic correlation ID for request tracing
client = HTTPClient(base_url="...")
response = client.get("/api/data")
# X-Correlation-ID header added automatically

# Custom correlation ID:
response = client.get(
    "/api/data",
    headers={'X-Correlation-ID': 'my-custom-id'}
)
```

### 4. Connection Pooling
```python
# Configure connection pool
config = HTTPClientConfig.create(
    base_url="...",
    pool_connections=20,  # Number of connection pools
    pool_maxsize=20,      # Max connections per pool
    max_redirects=10
)
client = HTTPClient(config=config)
```

## Quick Migration Checklist

- [ ] Update `max_retries` → `config.retry.max_attempts`
- [ ] Update `verify_ssl` → `config.security.verify_ssl`
- [ ] Remove direct attribute modifications
- [ ] Update exception handling for new hierarchy
- [ ] Test POST retry behavior (no longer retries by default)
- [ ] Add `.download()` for large file downloads
- [ ] Consider using explicit `HTTPClientConfig`

## Getting Help

- Documentation: See `docs/` directory
- Issues: Report issues on your project's issue tracker
- Examples: See `examples/` directory (if available)
