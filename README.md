# HTTP Client Core

[![Version](https://img.shields.io/badge/version-1.5.0-blue)](https://github.com/Git-Dalv/http-client-core)
[![Tests](https://img.shields.io/badge/tests-597%20passed-brightgreen)](https://github.com/Git-Dalv/http-client-core)
[![Coverage](https://img.shields.io/badge/coverage-80%25-green)](https://github.com/Git-Dalv/http-client-core)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Production-ready HTTP client library with powerful plugin system, intelligent retry logic, circuit breaker pattern, and comprehensive error handling.

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔄 **Smart Retry** | Exponential backoff with jitter, Retry-After header support |
| 🛡️ **Circuit Breaker** | Fault tolerance with automatic recovery |
| 🧩 **Plugin System** | 15+ built-in plugins, easy to extend |
| ⚡ **Async Support** | Full async/await API with httpx |
| 🔒 **Security** | Response size limits, decompression bomb protection, SSL verification |
| 📊 **Monitoring** | Built-in metrics, health checks, request tracing |
| 🌐 **Proxy Support** | Proxy rotation with health tracking |
| 🎭 **Browser Fingerprinting** | Realistic browser headers (Chrome, Firefox, Safari, Edge) |
| 📥 **Stream Downloads** | Memory-efficient large file downloads |
| 🔍 **Correlation ID** | Request tracing across distributed systems |
| ⚙️ **Hot Reload Config** | YAML/JSON config with file watching |
| 📡 **OpenTelemetry** | Distributed tracing and metrics |

## 📦 Installation

```bash
pip install http-client-core
```

### Optional Dependencies

```bash
# Async client (httpx)
pip install http-client-core[async]

# Progress bars for downloads
pip install http-client-core[progress]

# Disk caching
pip install http-client-core[cache]

# OpenTelemetry tracing & metrics
pip install http-client-core[otel]

# YAML config file support
pip install http-client-core[yaml]

# All optional dependencies
pip install http-client-core[all]
```

## 🚀 Quick Start

### Basic Usage

```python
from http_client import HTTPClient

# Simple GET request
client = HTTPClient(base_url="https://api.example.com")
response = client.get("/users")
print(response.json())

# POST with JSON
response = client.post("/users", json={"name": "John", "email": "john@example.com"})

# Always close or use context manager
client.close()
```

### Context Manager (Recommended)

```python
from http_client import HTTPClient

with HTTPClient(base_url="https://api.example.com") as client:
    response = client.get("/users")
    data = response.json()
# Automatically closed
```

### Async Client

```python
from http_client import AsyncHTTPClient
import asyncio

async def main():
    async with AsyncHTTPClient(base_url="https://api.example.com") as client:
        response = await client.get("/users")
        data = response.json()
        
        # Concurrent requests
        responses = await asyncio.gather(
            client.get("/users/1"),
            client.get("/users/2"),
            client.get("/users/3"),
        )

asyncio.run(main())
```

## ⚙️ Configuration

### Using HTTPClientConfig (Recommended)

```python
from http_client import (
    HTTPClient,
    HTTPClientConfig,
    TimeoutConfig,
    RetryConfig,
    SecurityConfig,
    CircuitBreakerConfig,
)

config = HTTPClientConfig(
    base_url="https://api.example.com",
    headers={"X-API-Key": "secret"},
    timeout=TimeoutConfig(
        connect=5,    # 5 seconds to connect
        read=30,      # 30 seconds to read response
        total=60,     # 60 seconds total
    ),
    retry=RetryConfig(
        max_attempts=5,
        backoff_base=0.5,
        backoff_factor=2.0,
        backoff_jitter=True,
        backoff_max=30.0,
        respect_retry_after=True,
        retryable_status_codes={500, 502, 503, 504, 429},
    ),
    security=SecurityConfig(
        verify_ssl=True,
        max_response_size=100 * 1024 * 1024,  # 100MB
        max_decompressed_size=500 * 1024 * 1024,  # 500MB
    ),
    circuit_breaker=CircuitBreakerConfig(
        enabled=True,
        failure_threshold=5,
        recovery_timeout=30.0,
        half_open_max_calls=3,
    ),
)

client = HTTPClient(config=config)
```

### Quick Factory Method

```python
from http_client import HTTPClientConfig

config = HTTPClientConfig.create(
    base_url="https://api.example.com",
    timeout=30,
    max_retries=5,
    verify_ssl=True,
)
```

### YAML Configuration

```yaml
# config.yaml
http_client:
  base_url: "https://api.example.com"
  timeout:
    connect: 5
    read: 30
  retry:
    max_attempts: 5
    backoff_factor: 2.0
  security:
    verify_ssl: true
  circuit_breaker:
    enabled: true
    failure_threshold: 5
```

```python
from http_client.core.env_config import ConfigFileLoader

config = ConfigFileLoader.from_yaml("config.yaml")
client = HTTPClient(config=config)
```

### Environment Variables

```bash
export HTTP_CLIENT_BASE_URL="https://api.example.com"
export HTTP_CLIENT_TIMEOUT_CONNECT=5
export HTTP_CLIENT_TIMEOUT_READ=30
export HTTP_CLIENT_RETRY_MAX_ATTEMPTS=5
export HTTP_CLIENT_SECURITY_VERIFY_SSL=true
```

```python
from http_client.core.env_config import EnvConfigLoader

config = EnvConfigLoader.load()
client = HTTPClient(config=config)
```

## 🧩 Plugins

### Built-in Plugins

| Plugin | Priority | Description |
|--------|----------|-------------|
| `BrowserFingerprintPlugin` | 0 (FIRST) | Realistic browser headers |
| `OpenTelemetryPlugin` | 0 (FIRST) | Distributed tracing |
| `AuthPlugin` | 10 (EARLY) | Authentication (Bearer, Basic, API Key) |
| `CachePlugin` | 10 (EARLY) | In-memory response caching |
| `DiskCachePlugin` | 10 (EARLY) | Persistent disk caching |
| `RateLimitPlugin` | 25 (HIGH) | Request rate limiting |
| `RetryPlugin` | 50 (NORMAL) | Custom retry logic |
| `LoggingPlugin` | 75 (LOW) | Request/response logging |
| `MonitoringPlugin` | 100 (LAST) | Metrics collection |

### Using Plugins

```python
from http_client import (
    HTTPClient,
    LoggingPlugin,
    MonitoringPlugin,
    CachePlugin,
    RateLimitPlugin,
    AuthPlugin,
)
from http_client.plugins import BrowserFingerprintPlugin

client = HTTPClient(base_url="https://api.example.com")

# Add plugins - they execute in priority order
client.add_plugin(BrowserFingerprintPlugin(browser="chrome"))
client.add_plugin(AuthPlugin(auth_type="bearer", token="your-token"))
client.add_plugin(CachePlugin(ttl=300, max_size=1000))
client.add_plugin(RateLimitPlugin(max_requests=100, time_window=60))
client.add_plugin(LoggingPlugin())
client.add_plugin(MonitoringPlugin())

response = client.get("/data")
```

### Authentication Plugin

```python
from http_client import HTTPClient, AuthPlugin

# Bearer token
auth = AuthPlugin(auth_type="bearer", token="your-api-token")

# Basic auth
auth = AuthPlugin(auth_type="basic", username="user", password="pass")

# API Key (header)
auth = AuthPlugin(auth_type="api_key", api_key="key", api_key_header="X-API-Key")

client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(auth)
```

### Caching Plugin

```python
from http_client import HTTPClient, CachePlugin

# In-memory cache with LRU eviction
cache = CachePlugin(
    ttl=300,       # Cache for 5 minutes
    max_size=1000  # Max 1000 entries
)

client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(cache)

# First request hits API
response1 = client.get("/users")

# Second request served from cache
response2 = client.get("/users")

# Check cache stats
print(f"Cache size: {cache.size}/{cache.max_size}")
print(f"Hit rate: {cache.hits / (cache.hits + cache.misses) * 100:.1f}%")
```

### Rate Limiting Plugin

```python
from http_client import HTTPClient, RateLimitPlugin

# 100 requests per 60 seconds
rate_limiter = RateLimitPlugin(max_requests=100, time_window=60)

client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(rate_limiter)

# Requests automatically throttled when limit reached
for i in range(200):
    response = client.get(f"/data/{i}")
```

### Browser Fingerprint Plugin

```python
from http_client import HTTPClient
from http_client.plugins import BrowserFingerprintPlugin

# Imitate Chrome browser
plugin = BrowserFingerprintPlugin(browser="chrome")

# Or Firefox, Safari, Edge, chrome_mobile
plugin = BrowserFingerprintPlugin(browser="firefox")

# Random browser for each request (anti-bot evasion)
plugin = BrowserFingerprintPlugin(random_profile=True)

client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(plugin)

# Available browsers
print(BrowserFingerprintPlugin.get_available_browsers())
# ['chrome', 'firefox', 'safari', 'edge', 'chrome_mobile']
```

### Monitoring Plugin

```python
from http_client import HTTPClient, MonitoringPlugin

monitoring = MonitoringPlugin()
client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(monitoring)

# Make requests
for i in range(10):
    client.get(f"/users/{i}")

# Get metrics
metrics = monitoring.get_metrics()
print(f"Total requests: {metrics['total_requests']}")
print(f"Success rate: {metrics['success_rate']:.1%}")
print(f"Avg response time: {metrics['avg_response_time']:.2f}s")
print(f"Requests by status: {metrics['status_codes']}")
```

## 🛡️ Circuit Breaker

Protect your application from cascading failures:

```python
from http_client import HTTPClient, HTTPClientConfig, CircuitBreakerConfig

config = HTTPClientConfig(
    base_url="https://api.example.com",
    circuit_breaker=CircuitBreakerConfig(
        enabled=True,
        failure_threshold=5,    # Open after 5 failures
        recovery_timeout=30.0,  # Try recovery after 30s
        half_open_max_calls=3,  # Allow 3 test requests
    ),
)

client = HTTPClient(config=config)

# Circuit states: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
# When OPEN, requests fail immediately with CircuitOpenError
```

## 📥 File Downloads

### Basic Download

```python
from http_client import HTTPClient

client = HTTPClient(base_url="https://example.com")

# Stream download (memory-efficient)
bytes_downloaded = client.download(
    "/large-file.zip",
    "output.zip",
    chunk_size=8192,
)
print(f"Downloaded {bytes_downloaded} bytes")
```

### Download with Progress

```python
from http_client import HTTPClient

def on_progress(downloaded, total):
    if total > 0:
        percent = (downloaded / total) * 100
        print(f"\rProgress: {percent:.1f}%", end="")

client = HTTPClient(base_url="https://example.com")
client.download(
    "/large-file.zip",
    "output.zip",
    progress_callback=on_progress,
)
```

### Async Download

```python
from http_client import AsyncHTTPClient

async with AsyncHTTPClient() as client:
    bytes_downloaded = await client.download(
        "https://example.com/file.zip",
        "output.zip",
        chunk_size=8192,
    )
```

## 🔍 Health Checks

```python
from http_client import HTTPClient

client = HTTPClient(base_url="https://api.example.com")

# Basic health check
health = client.health_check()
print(f"Healthy: {health['healthy']}")
print(f"Active sessions: {health['active_sessions']}")
print(f"Plugins: {health['plugins']}")

# With connectivity test
health = client.health_check(test_url="https://api.example.com/health")
if health['connectivity']['reachable']:
    print(f"✅ API reachable in {health['connectivity']['response_time_ms']}ms")
else:
    print(f"❌ API unreachable: {health['connectivity']['error']}")
```

## 📡 OpenTelemetry Integration

```python
from http_client import HTTPClient
from http_client.contrib.opentelemetry import OpenTelemetryPlugin, OpenTelemetryMetrics

# Setup OpenTelemetry (see opentelemetry-python docs)
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    SimpleSpanProcessor(ConsoleSpanExporter())
)

# Add tracing to HTTP client
client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(OpenTelemetryPlugin())
client.add_plugin(OpenTelemetryMetrics())

# Requests are now traced
response = client.get("/users")
```

## 🌐 Proxy Support

```python
from http_client import HTTPClient, HTTPClientConfig
from http_client.utils.proxy_manager import ProxyPool

# Simple proxy
config = HTTPClientConfig(
    base_url="https://api.example.com",
    proxies={
        "http://": "http://proxy.example.com:8080",
        "https://": "http://proxy.example.com:8080",
    },
)
client = HTTPClient(config=config)

# Proxy pool with rotation
pool = ProxyPool()
pool.add_proxy("proxy1.example.com", 8080)
pool.add_proxy("proxy2.example.com", 8080)
pool.add_proxy("proxy3.example.com", 8080)

# Get best proxy (round-robin with health tracking)
proxy = pool.get_proxy()
```

## ⚠️ Exception Handling

```python
from http_client import (
    HTTPClient,
    HTTPClientException,
    TimeoutError,
    ConnectionError,
    ServerError,
    NotFoundError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    TooManyRetriesError,
    CircuitOpenError,
    ResponseTooLargeError,
)

client = HTTPClient(base_url="https://api.example.com")

try:
    response = client.get("/resource")
except TimeoutError as e:
    print(f"Request timed out: {e}")
except ConnectionError as e:
    print(f"Connection failed: {e}")
except NotFoundError as e:
    print(f"Resource not found: {e.status_code}")
except UnauthorizedError as e:
    print(f"Authentication required: {e}")
except ForbiddenError as e:
    print(f"Access denied: {e}")
except BadRequestError as e:
    print(f"Invalid request: {e}")
except ServerError as e:
    print(f"Server error ({e.status_code}): {e}")
except TooManyRetriesError as e:
    print(f"Max retries exceeded: {e}")
except CircuitOpenError as e:
    print(f"Circuit breaker open: {e}")
except ResponseTooLargeError as e:
    print(f"Response too large: {e}")
except HTTPClientException as e:
    print(f"HTTP client error: {e}")
```

### Exception Hierarchy

```
HTTPClientException
├── TemporaryError (retryable)
│   ├── NetworkError
│   │   ├── TimeoutError
│   │   ├── ConnectionError
│   │   ├── ProxyError
│   │   └── DNSError
│   ├── ServerError (5xx)
│   └── TooManyRequestsError (429)
└── FatalError (not retryable)
    ├── HTTPError (4xx)
    │   ├── BadRequestError (400)
    │   ├── UnauthorizedError (401)
    │   ├── ForbiddenError (403)
    │   └── NotFoundError (404)
    ├── InvalidResponseError
    ├── ResponseTooLargeError
    ├── DecompressionBombError
    └── CircuitOpenError
```

## 🔄 Hot Reload Configuration

For long-running applications:

```python
from http_client import ReloadableHTTPClient

# Automatically reloads config when file changes
client = ReloadableHTTPClient(config_path="config.yaml")

# Or with environment variable
# HTTP_CLIENT_CONFIG_FILE=config.yaml
client = ReloadableHTTPClient()
```

## 📋 API Reference

### HTTPClient Methods

| Method | Description |
|--------|-------------|
| `get(url, **kwargs)` | GET request |
| `post(url, **kwargs)` | POST request |
| `put(url, **kwargs)` | PUT request |
| `patch(url, **kwargs)` | PATCH request |
| `delete(url, **kwargs)` | DELETE request |
| `head(url, **kwargs)` | HEAD request |
| `options(url, **kwargs)` | OPTIONS request |
| `request(method, url, **kwargs)` | Generic request |
| `download(url, path, **kwargs)` | Stream download |
| `health_check(test_url=None)` | Health diagnostics |
| `add_plugin(plugin)` | Add plugin |
| `remove_plugin(plugin)` | Remove plugin |
| `close()` | Close client |

### AsyncHTTPClient Methods

Same as HTTPClient, but all methods are async (use `await`).

## ⚠️ Deprecation Notices

The following parameters are deprecated and will be removed in v2.0.0:

| Deprecated | Use Instead |
|------------|-------------|
| `max_retries` | `config.retry.max_attempts` |
| `verify_ssl` | `config.security.verify_ssl` |
| `pool_connections` | `config.pool.pool_connections` |
| `pool_maxsize` | `config.pool.pool_maxsize` |
| `max_redirects` | `config.pool.max_redirects` |

See [Migration Guide](docs/migration/v1-to-v2.md) for details.

## 🧪 Development

```bash
# Clone repository
git clone https://github.com/Git-Dalv/http-client-core.git
cd http-client-core

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/http_client --cov-report=html

# Code quality checks
python scripts/check.py

# Format code
black src tests
ruff check src tests --fix
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) first.

## 📚 Documentation

- [Migration Guide](docs/migration/v1-to-v2.md)
- [Plugin Development](docs/plugins.md)
- [Examples](examples/)
- [Changelog](CHANGELOG.md)

## 🔗 Links

- **Repository**: https://github.com/Git-Dalv/http-client-core
- **Issues**: https://github.com/Git-Dalv/http-client-core/issues
- **PyPI**: https://pypi.org/project/http-client-core/
