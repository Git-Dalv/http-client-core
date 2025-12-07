# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2024-12-07

### Added
- **HTTPClient.health_check()** method for monitoring and diagnostics
  - Returns comprehensive diagnostic information (base_url, active sessions, plugins, config)
  - Optional connectivity test with response time measurement
  - Suitable for Kubernetes probes, Prometheus endpoints, and debugging
  - Example: `health = client.health_check(test_url="https://api.example.com/health")`

- **CachePlugin.max_size** parameter for limiting cache entries (default: 1000)
  - Prevents unbounded cache growth in long-running applications
  - Automatic eviction using LRU (Least Recently Used) strategy
  - Removes 10% of oldest entries when limit is reached (amortized eviction)

- **CachePlugin statistics properties** for monitoring cache performance
  - `cache.size` - Current number of cached entries (thread-safe)
  - `cache.hits` - Number of cache hits
  - `cache.misses` - Number of cache misses
  - `cache.max_size` - Maximum cache size limit

### Changed
- **RetryPlugin** now uses `logging` module instead of `print()` statements
  - `logger.info()` for retry messages
  - `logger.error()` for max retries exhausted messages
  - Production-ready logging with configurable log levels

- **CachePlugin** now automatically manages memory with LRU eviction
  - Old entries are automatically removed when `max_size` is reached
  - Thread-safe eviction (called within lock)
  - No breaking changes - existing code works without modification

### Fixed
- Memory leak in `CachePlugin` when cache grows indefinitely
  - Cache now respects `max_size` limit and evicts old entries
  - Prevents out-of-memory errors in long-running applications

### Performance
- Improved cache efficiency with LRU eviction strategy
- Thread-safe hit/miss tracking with minimal overhead
- Health checks use HEAD requests for minimal network impact

### Tests
- Added 19 comprehensive tests for `HTTPClient.health_check()`
- Added 19 comprehensive tests for `CachePlugin` max_size and statistics
- Updated RetryPlugin tests to verify logger usage
- All tests passing (597 unit tests, 80.60% coverage)

### Documentation
- Updated README.md with health check examples
- Updated README.md with cache statistics examples
- Added use cases for monitoring and observability

## [1.0.0] - 2024-12-06

### Initial Release
- Production-ready HTTP client with plugin system
- Smart retry logic with exponential backoff
- Type-safe configuration with immutable config objects
- 10+ built-in plugins
- Comprehensive error handling
- 415 tests with 85% coverage

---

[Unreleased]: https://github.com/Git-Dalv/http-client-core/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/Git-Dalv/http-client-core/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/Git-Dalv/http-client-core/releases/tag/v1.0.0
