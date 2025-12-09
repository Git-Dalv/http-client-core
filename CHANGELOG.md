# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Migration guide for v1.x to v2.0 transition
- Migration checker tool: `python -m http_client.tools.migration_check`
- Hot reload configuration support for long-running processes
- `ReloadableHTTPClient` for automatic config reloading
- `ConfigWatcher` for monitoring config file changes
- YAML/JSON configuration file loading support
- Example configuration files in `docs/examples/`

### Deprecated
- `LoggingPlugin` - use `HTTPClientConfig.logging` instead
- Constructor parameters in favor of structured config objects:
  - `max_retries` → `config.retry.max_attempts`
  - `pool_connections` → `config.pool.pool_connections`
  - `pool_maxsize` → `config.pool.pool_maxsize`
  - `max_redirects` → `config.pool.max_redirects`
  - `verify_ssl` → `config.security.verify_ssl`
  - `pool_block` → `config.pool.pool_block`

### Changed
- Improved deprecation warnings with migration guide links
- Enhanced documentation with migration examples

## [1.0.0] - 2024-XX-XX

### Added
- Production-ready HTTP client with plugin system
- Intelligent retry logic with exponential backoff
- Thread-safe session management
- Circuit breaker pattern for fault tolerance
- Connection pooling
- OpenTelemetry integration for tracing and metrics
- Comprehensive plugin ecosystem:
  - LoggingPlugin
  - MonitoringPlugin
  - CachePlugin
  - RateLimitPlugin
  - AuthPlugin
  - BrowserFingerprintPlugin
- Type-safe immutable configuration
- Response size limits and decompression bomb protection
- Health check endpoint

### Security
- SSL verification enabled by default
- Response size limits to prevent memory exhaustion
- Decompression bomb protection
- Secret masking in logs

## Deprecation Timeline

- **v1.5.0** (Current): Deprecation warnings added
- **v1.9.0** (Future): Warnings become errors in strict mode
- **v2.0.0** (Future): Deprecated APIs removed

## Migration Resources

- **Migration Guide**: [docs/migration/v1-to-v2.md](docs/migration/v1-to-v2.md)
- **Migration Checker**: `python -m http_client.tools.migration_check`
- **Strict Mode**: `HTTP_CLIENT_STRICT_DEPRECATION=1`

## Links

- **Repository**: https://github.com/Git-Dalv/http-client-core
- **Documentation**: https://github.com/Git-Dalv/http-client-core/tree/main/docs
- **Issues**: https://github.com/Git-Dalv/http-client-core/issues
