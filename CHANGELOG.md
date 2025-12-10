# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0] - 2024-12-10

### Added

- **AsyncHTTPClient**: Full async/await support with httpx backend
  - Async context manager support
  - Async download with progress callback
  - Async circuit breaker
  - Async plugin system with `AsyncPlugin` base class
  - `AsyncCachePlugin`, `AsyncRateLimitPlugin`, `AsyncMonitoringPlugin`
  
- **Circuit Breaker**: Fault tolerance pattern for cascading failure protection
  - Three states: CLOSED, OPEN, HALF_OPEN
  - Configurable failure threshold and recovery timeout
  - Excluded exceptions support
  - Both sync and async implementations
  
- **Hot Reload Configuration**: For long-running applications
  - `ReloadableHTTPClient` with automatic config reloading
  - `ConfigWatcher` for file change monitoring
  - YAML/JSON configuration file support
  - Environment variable configuration loader
  
- **Browser Fingerprint Plugin**: Anti-bot detection evasion
  - Chrome, Firefox, Safari, Edge, Chrome Mobile profiles
  - Random profile mode for rotation
  - Consistent Client Hints headers
  
- **OpenTelemetry Integration**: Distributed tracing and metrics
  - `OpenTelemetryPlugin` for request tracing
  - `OpenTelemetryMetrics` for request metrics
  - W3C Trace Context propagation
  - Semantic conventions compliance
  
- **Proxy Pool Manager**: Advanced proxy management
  - Health tracking per proxy
  - Automatic rotation strategies
  - Concurrent proxy checking with ThreadPoolExecutor
  - Deadlock-free implementation
  
- **Plugin Priority System**: Ordered plugin execution
  - `PluginPriority` enum: FIRST(0), EARLY(10), HIGH(25), NORMAL(50), LOW(75), LAST(100)
  - Automatic sorting by priority
  - `get_plugins_order()` for debugging

### Changed

- **CachePlugin**: Added LRU eviction with `max_size` parameter (default 1000)
- **RetryPlugin**: Replaced print() with proper logging module
- **Session Management**: Thread-safe double-checked locking pattern
- **Exception Handling**: Improved Retry-After header parsing with security validations
- **Documentation**: Comprehensive README rewrite with examples

### Fixed

- Memory leak in CachePlugin for long-running applications
- Deadlock in ProxyPool with check_on_add=True
- Thread-safety issues in RateLimitPlugin
- Retry-After header DoS vulnerability (oversized header protection)

### Security

- Response size limits (default 100MB)
- Decompression bomb protection (default 500MB decompressed)
- SSL verification enabled by default
- Sensitive URL parameter masking in logs
- Secret masking in logging output

## [1.0.1] - 2024-12-07

### Added

- `health_check()` method for monitoring and diagnostics
- Cache statistics: `size`, `hits`, `misses`, `max_size` properties
- Health check with optional connectivity test

### Changed

- RetryPlugin: All print() replaced with logging module
- CachePlugin: Added max_size with LRU eviction

### Fixed

- Production logging in RetryPlugin
- Memory leaks in CachePlugin

## [1.0.0] - 2024-12-01

### Added

- Production-ready HTTP client with plugin system
- Intelligent retry logic with exponential backoff and jitter
- Thread-safe session management with connection pooling
- Comprehensive plugin ecosystem:
  - `LoggingPlugin` - Request/response logging
  - `RetryPlugin` - Custom retry logic  
  - `CachePlugin` - In-memory response caching
  - `DiskCachePlugin` - Persistent disk caching
  - `RateLimitPlugin` - Request rate limiting
  - `AuthPlugin` - Authentication (Bearer, Basic, API Key)
  - `MonitoringPlugin` - Metrics collection
- Type-safe immutable configuration with dataclasses
- Stream downloads for large files
- Correlation ID for request tracing
- Comprehensive exception hierarchy

### Security

- SSL verification enabled by default
- Response size limits
- Decompression bomb protection

---

## Deprecation Timeline

| Version | Status | Description |
|---------|--------|-------------|
| 1.5.0 | Current | Deprecation warnings added |
| 1.9.0 | Future | Warnings become errors in strict mode |
| 2.0.0 | Future | Deprecated APIs removed |

### Deprecated Parameters

| Parameter | Replacement | Deprecated In | Removed In |
|-----------|-------------|---------------|------------|
| `max_retries` | `config.retry.max_attempts` | 1.0.0 | 2.0.0 |
| `verify_ssl` | `config.security.verify_ssl` | 1.0.0 | 2.0.0 |
| `pool_connections` | `config.pool.pool_connections` | 1.0.0 | 2.0.0 |
| `pool_maxsize` | `config.pool.pool_maxsize` | 1.0.0 | 2.0.0 |
| `max_redirects` | `config.pool.max_redirects` | 1.0.0 | 2.0.0 |
| `pool_block` | `config.pool.pool_block` | 1.0.0 | 2.0.0 |

---

## Migration Resources

- **Migration Guide**: [docs/migration/v1-to-v2.md](docs/migration/v1-to-v2.md)
- **Migration Checker**: `python -m http_client.tools.migration_check`
- **Strict Mode**: `HTTP_CLIENT_STRICT_DEPRECATION=1`

---

## Links

- **Repository**: https://github.com/Git-Dalv/http-client-core
- **Documentation**: https://github.com/Git-Dalv/http-client-core#readme
- **Issues**: https://github.com/Git-Dalv/http-client-core/issues
- **PyPI**: https://pypi.org/project/http-client-core/
