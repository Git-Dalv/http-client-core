# HTTP Client Core

[![Tests](https://img.shields.io/badge/tests-415%20passed-brightgreen)](https://github.com/Git-Dalv/http-client-core)
[![Coverage](https://img.shields.io/badge/coverage-85%25-green)](https://github.com/Git-Dalv/http-client-core)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Production-ready HTTP client library with powerful plugin system, intelligent retry logic, and comprehensive error handling.

## ✨ Features

- 🔄 **Smart Retry Logic** - Exponential backoff, jitter, Retry-After header support
- 🧩 **Plugin System** - Modular architecture with 10+ built-in plugins
- 🛡️ **Type-Safe Config** - Immutable configuration with full type hints
- 🔒 **Security** - Response size limits, decompression bomb protection
- 📊 **Monitoring** - Built-in metrics, request tracking, performance stats
- 🌐 **Proxy Support** - Proxy rotation with health tracking
- 🎭 **Browser Fingerprinting** - Realistic browser headers (Chrome, Firefox, Safari)
- ⚡ **Connection Pooling** - Efficient HTTP connection management
- 📥 **Stream Downloads** - Memory-efficient large file downloads
- 🔍 **Correlation ID** - Request tracing across distributed systems

## 📦 Installation

```bash
pip install http-client-core

# With progress bar support for downloads
pip install http-client-core[progress]

# With all optional dependencies
pip install http-client-core[all]
```

## 🚀 Quick Start

```python
from src.http_client import HTTPClient

# Simple GET request
client = HTTPClient(base_url="https://api.example.com")
response = client.get("/users")
print(response.json())

# POST with JSON
response = client.post("/users", json={"name": "John", "email": "john@example.com"})
```

## 🎯 Basic Examples

### With Automatic Retry

```python
from src.http_client import HTTPClient

# Automatic retry on 5xx errors and timeouts
client = HTTPClient(
    base_url="https://api.example.com",
    max_retries=3,  # Retry up to 3 times
    timeout=30       # 30 second timeout
)

response = client.get("/data")
# Will automatically retry on: 500, 502, 503, 504, timeouts
```

### Advanced Configuration

```python
from src.http_client import HTTPClientConfig, TimeoutConfig, RetryConfig

config = HTTPClientConfig(
    base_url="https://api.example.com",
    timeout=TimeoutConfig(
        connect=5,   # 5 seconds to connect
        read=30      # 30 seconds to read response
    ),
    retry=RetryConfig(
        max_attempts=5,
        backoff_base=0.5,
        backoff_factor=2.0,
        backoff_jitter=True,
        respect_retry_after=True
    )
)

client = HTTPClient(config=config)
```

### Download Large Files

```python
# Stream download to avoid memory issues
client = HTTPClient(base_url="https://example.com")

bytes_downloaded = client.download(
    "/large-file.zip",
    "output.zip",
    chunk_size=8192,
    show_progress=True  # Requires tqdm
)

print(f"Downloaded {bytes_downloaded} bytes")
```

## 🧩 Plugins

### Logging Plugin

```python
from src.http_client import HTTPClient, LoggingPlugin

client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(LoggingPlugin())

# All requests will be logged
response = client.get("/data")
# [INFO] Sending GET request to https://api.example.com/data
# [INFO] Response 200 from https://api.example.com/data (took 0.5s)
```

### Monitoring Plugin

```python
from src.http_client import HTTPClient, MonitoringPlugin

monitoring = MonitoringPlugin()
client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(monitoring)

# Make requests
for i in range(10):
    client.get(f"/users/{i}")

# Get metrics
metrics = monitoring.get_metrics()
print(f"Total requests: {metrics['total_requests']}")
print(f"Success rate: {metrics['success_rate']}")
print(f"Avg response time: {metrics.get('avg_response_time', 0):.2f}s")
```

### Rate Limiting

```python
from src.http_client import HTTPClient, RateLimitPlugin

# Limit to 5 requests per second
rate_limiter = RateLimitPlugin(max_requests_per_second=5)
client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(rate_limiter)

# These requests will be automatically rate-limited
for i in range(20):
    response = client.get(f"/data/{i}")
```

### Authentication

```python
from src.http_client import HTTPClient, AuthPlugin

# Bearer token authentication
auth = AuthPlugin(auth_type="bearer", token="your-api-token")
client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(auth)

# All requests will include: Authorization: Bearer your-api-token
response = client.get("/protected-resource")
```

## 📚 More Examples

### Response Caching

```python
from src.http_client import HTTPClient, CachePlugin

cache = CachePlugin(ttl=300)  # Cache for 5 minutes
client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(cache)

# First request hits the API
response1 = client.get("/data")

# Second request uses cache (much faster!)
response2 = client.get("/data")
```

### Using Multiple Plugins

```python
from src.http_client import HTTPClient, LoggingPlugin, MonitoringPlugin, RateLimitPlugin

client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(LoggingPlugin())
client.add_plugin(MonitoringPlugin())
client.add_plugin(RateLimitPlugin(max_requests_per_second=10))

# All plugins work together
for i in range(50):
    response = client.get(f"/data/{i}")
```

## 🔧 Configuration

### Timeout Configuration

```python
from src.http_client import HTTPClientConfig, TimeoutConfig

config = HTTPClientConfig(
    base_url="https://api.example.com",
    timeout=TimeoutConfig(
        connect=5,   # Connection timeout
        read=30,     # Read timeout
        total=None   # Total timeout (optional)
    )
)
```

### Retry Configuration

```python
from src.http_client import RetryConfig

retry = RetryConfig(
    max_attempts=3,
    backoff_base=0.5,           # Initial backoff: 0.5s
    backoff_factor=2.0,          # Exponential: 0.5s, 1s, 2s, 4s...
    backoff_max=60.0,            # Max backoff: 60s
    backoff_jitter=True,         # Add randomness (±50%)
    respect_retry_after=True,    # Respect Retry-After header
    retry_after_max=300,         # Max Retry-After: 5 minutes
    
    # Which methods to retry (only idempotent by default)
    idempotent_methods={'GET', 'HEAD', 'PUT', 'DELETE', 'OPTIONS', 'TRACE'},
    
    # Which status codes to retry
    retryable_status_codes={408, 429, 500, 502, 503, 504}
)
```

### Security Configuration

```python
from src.http_client import SecurityConfig

security = SecurityConfig(
    max_response_size=100 * 1024 * 1024,      # 100MB
    max_decompressed_size=500 * 1024 * 1024,  # 500MB
    verify_ssl=True,
    allow_redirects=True
)
```

### Connection Pool Configuration

```python
from src.http_client import ConnectionPoolConfig

pool = ConnectionPoolConfig(
    pool_connections=10,   # Number of connection pools
    pool_maxsize=10,       # Max connections per pool
    pool_block=False,      # Don't block when pool is full
    max_redirects=30       # Max redirects to follow
)
```

## 🎭 Available Plugins

| Plugin | Description |
|--------|-------------|
| **LoggingPlugin** | Log all requests and responses |
| **MonitoringPlugin** | Track metrics and performance |
| **RetryPlugin** | Custom retry logic (legacy) |
| **CachePlugin** | In-memory response caching |
| **RateLimitPlugin** | Limit requests per second |
| **AuthPlugin** | Bearer token / API key auth |

## 🔄 Exception Handling

```python
from src.http_client import HTTPClient
from src.http_client import (
    HTTPError,
    NotFoundError,
    ServerError,
    TimeoutError,
    TooManyRetriesError
)

client = HTTPClient(base_url="https://api.example.com")

try:
    response = client.get("/data")
except NotFoundError as e:
    print(f"Resource not found: {e}")
except ServerError as e:
    print(f"Server error (will be retried automatically): {e}")
except TimeoutError as e:
    print(f"Request timeout: {e}")
except TooManyRetriesError as e:
    print(f"Max retries exceeded: {e}")
except HTTPError as e:
    print(f"HTTP error: {e}")
```

## 🔄 Migration from v0.x

See [docs/MIGRATION.md](docs/MIGRATION.md) for detailed migration guide.

**Key Changes:**
- Configuration system (immutable config objects)
- POST requests no longer retry by default
- New exception hierarchy (TemporaryError vs FatalError)
- Deprecation warnings for old parameters

**Quick Migration:**

```python
# Old (v0.x) - Still works with warnings
client = HTTPClient(
    base_url="https://api.example.com",
    max_retries=3,
    verify_ssl=True
)

# New (v1.0) - Recommended
from src.http_client import HTTPClientConfig

config = HTTPClientConfig.create(
    base_url="https://api.example.com",
    max_retries=3
)
client = HTTPClient(config=config)
```

## 📖 Documentation

- **[Migration Guide](docs/MIGRATION.md)** - Upgrade from v0.x to v1.0
- **[Examples](examples/)** - Complete code examples (coming soon)

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/http_client --cov-report=html

# Run specific test file
pytest tests/unit/core/test_http_client.py -v

# Run only unit tests
pytest -m unit
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with:
- [requests](https://requests.readthedocs.io/) - HTTP for Humans
- [pytest](https://pytest.org/) - Testing framework
- [responses](https://github.com/getsentry/responses) - Mocking library

## 📊 Project Stats

- ✅ **415** tests passed
- ✅ **85%** code coverage
- ✅ **1.0.0** production-ready
- ✅ **10+** built-in plugins
- ✅ **Type-safe** configuration
- ✅ **Immutable** config objects
- ✅ **Python 3.9+** support

---

**Made with ❤️ for the Python community**
