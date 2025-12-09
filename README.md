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

# With optional dependencies
pip install http-client-core[progress]    # Progress bars for downloads
pip install http-client-core[async]       # Async client (httpx)
pip install http-client-core[cache]       # Disk caching
pip install http-client-core[otel]        # OpenTelemetry tracing & metrics
pip install http-client-core[yaml]        # YAML config file support

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

## 📝 Configuration Files

Load configuration from YAML or JSON files for easier management and deployment:

### YAML Configuration

```bash
# Install YAML support
pip install http-client-core[yaml]
```

```python
from http_client import HTTPClient
from http_client.core.env_config import ConfigFileLoader

# Load from YAML file
config = ConfigFileLoader.from_yaml("config.yaml")
client = HTTPClient(config=config)

# Or auto-detect format by extension
config = ConfigFileLoader.from_file("config.yaml")
client = HTTPClient(config=config)

# Or use environment variable
# export HTTP_CLIENT_CONFIG_FILE=/path/to/config.yaml
config = ConfigFileLoader.from_env_path()
if config:
    client = HTTPClient(config=config)
```

**Example config.yaml:**

```yaml
http_client:
  base_url: "https://api.example.com"

  headers:
    Authorization: "Bearer YOUR_TOKEN_HERE"
    User-Agent: "MyApp/1.0"

  timeout:
    connect: 5
    read: 30
    total: 60

  retry:
    max_attempts: 3
    backoff_factor: 2.0
    backoff_jitter: true

  security:
    verify_ssl: true
    max_response_size: 104857600  # 100MB
```

### JSON Configuration

```python
from http_client.core.env_config import ConfigFileLoader

# Load from JSON file
config = ConfigFileLoader.from_json("config.json")
client = HTTPClient(config=config)
```

**Example config.json:**

```json
{
  "http_client": {
    "base_url": "https://api.example.com",
    "headers": {
      "Authorization": "Bearer YOUR_TOKEN_HERE"
    },
    "timeout": {
      "connect": 5,
      "read": 30
    },
    "retry": {
      "max_attempts": 3
    }
  }
}
```

### Configuration Examples

See complete configuration examples in [docs/examples/](docs/examples/):
- [config.yaml](docs/examples/config.yaml) - Full example with all options
- [config-minimal.yaml](docs/examples/config-minimal.yaml) - Minimal configuration
- [config-production.yaml](docs/examples/config-production.yaml) - Production-ready setup
- [config-kubernetes.yaml](docs/examples/config-kubernetes.yaml) - Kubernetes ConfigMap

### Environment Variable

Set `HTTP_CLIENT_CONFIG_FILE` to automatically load configuration:

```bash
export HTTP_CLIENT_CONFIG_FILE=/etc/myapp/http-client.yaml
```

```python
from http_client import HTTPClient
from http_client.core.env_config import ConfigFileLoader

# Automatically loads from HTTP_CLIENT_CONFIG_FILE
config = ConfigFileLoader.from_env_path()
client = HTTPClient(config=config)
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

## 🔍 Monitoring & Health Checks

### Health Check

The `health_check()` method provides comprehensive diagnostics for monitoring systems, health endpoints, and debugging:

```python
from src.http_client import HTTPClient

client = HTTPClient(base_url="https://api.example.com")

# Basic health check (no network request)
health = client.health_check()
print(f"Healthy: {health['healthy']}")
print(f"Active sessions: {health['active_sessions']}")
print(f"Plugins: {health['plugins']}")
print(f"Config: {health['config']}")

# Health check with connectivity test
health = client.health_check(test_url="https://api.example.com/health")
if health['connectivity']['reachable']:
    print(f"✅ API reachable in {health['connectivity']['response_time_ms']}ms")
else:
    print(f"❌ API unreachable: {health['connectivity']['error']}")
```

**Use cases:**
- Kubernetes liveness/readiness probes
- Prometheus metrics endpoints
- Pre-deployment connectivity checks
- Debugging connection issues

### Cache Statistics

Monitor cache performance with built-in metrics:

```python
from src.http_client import HTTPClient, CachePlugin

# Create cache with size limit
cache = CachePlugin(ttl=300, max_size=100)

client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(cache)

# Make requests
client.get("/users")
client.get("/users")  # Cache hit

# Check statistics
print(f"Cache size: {cache.size}/{cache.max_size}")
print(f"Hit rate: {cache.hits / (cache.hits + cache.misses) * 100:.1f}%")
print(f"Cache hits: {cache.hits}")
print(f"Cache misses: {cache.misses}")
```

**Features:**
- Automatic eviction with LRU strategy
- Thread-safe hit/miss tracking
- Configurable max_size to prevent memory leaks

## 📡 OpenTelemetry Integration

Add distributed tracing and metrics using OpenTelemetry (industry standard for observability):

### Installation

```bash
pip install http-client-core[otel]
```

### Distributed Tracing

Track HTTP requests across your distributed system with OpenTelemetry tracing:

```python
from http_client import HTTPClient
from http_client.contrib.opentelemetry import OpenTelemetryPlugin

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

# Setup OpenTelemetry tracer
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)

# Add OpenTelemetry plugin
client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(OpenTelemetryPlugin())

# All requests are now traced automatically
response = client.get("/users")
```

**Features:**
- Automatic span creation for each HTTP request
- W3C Trace Context propagation in headers
- Follows OpenTelemetry Semantic Conventions
- Captures request/response metadata
- Records exceptions and errors
- Filters sensitive headers (Authorization, Cookie, etc.)

### Metrics Collection

Collect HTTP client metrics using OpenTelemetry:

```python
from http_client import HTTPClient
from http_client.contrib.opentelemetry import OpenTelemetryMetrics

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)

# Setup OpenTelemetry metrics
reader = PeriodicExportingMetricReader(ConsoleMetricExporter())
provider = MeterProvider(metric_readers=[reader])
metrics.set_meter_provider(provider)

# Add metrics plugin
client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(OpenTelemetryMetrics())

# Metrics collected automatically:
# - http_client_requests_total (counter)
# - http_client_request_duration_seconds (histogram)
# - http_client_active_requests (gauge)
response = client.get("/users")
```

### Integration with Jaeger

Export traces to Jaeger for visualization:

```python
from http_client import HTTPClient
from http_client.contrib.opentelemetry import OpenTelemetryPlugin

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

# Setup Jaeger exporter
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
trace.set_tracer_provider(provider)

# Use plugin
client = HTTPClient(base_url="https://api.example.com")
client.add_plugin(OpenTelemetryPlugin())

# Traces exported to Jaeger automatically
response = client.get("/users")
```

### Advanced Configuration

Customize OpenTelemetry behavior:

```python
from http_client.contrib.opentelemetry import OpenTelemetryPlugin

plugin = OpenTelemetryPlugin(
    tracer_name="my_service",
    record_request_body=True,   # Include request body in spans
    record_response_body=True,  # Include response body in spans
    excluded_urls=["health", "metrics"],  # Don't trace these URLs
    capture_headers=True,        # Capture HTTP headers (sensitive ones filtered)
    max_header_length=256,       # Truncate long header values
)

client.add_plugin(plugin)
```

**Use Cases:**
- Distributed tracing in microservices
- Performance monitoring and bottleneck identification
- Error tracking and debugging
- SLO/SLA monitoring
- Integration with Jaeger, Zipkin, Prometheus, Grafana

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
