"""
Pydantic validators for environment configuration.

Provides validated models for all configuration options.
"""

from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TimeoutSettings(BaseModel):
    """Timeout configuration from environment."""

    connect: float = Field(default=5.0, gt=0, description="Connect timeout in seconds")
    read: float = Field(default=10.0, gt=0, description="Read timeout in seconds")
    total: Optional[float] = Field(default=30.0, gt=0, description="Total timeout in seconds")

    @field_validator('total')
    @classmethod
    def validate_total(cls, v: Optional[float], info) -> Optional[float]:
        """Validate that total >= connect + read."""
        if v is not None:
            connect = info.data.get('connect', 5.0)
            read = info.data.get('read', 10.0)
            if v < (connect + read):
                raise ValueError(f"total timeout ({v}) must be >= connect ({connect}) + read ({read})")
        return v


class RetrySettings(BaseModel):
    """Retry configuration from environment."""

    max_attempts: int = Field(default=3, ge=1, le=10, description="Maximum retry attempts")
    backoff_factor: float = Field(default=2.0, ge=1.0, description="Exponential backoff factor")
    backoff_jitter: bool = Field(default=True, description="Enable random jitter")
    backoff_max: float = Field(default=60.0, gt=0, description="Maximum wait time between retries")


class SecuritySettings(BaseModel):
    """Security configuration from environment."""

    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    max_response_size: int = Field(default=100 * 1024 * 1024, gt=0, description="Max response size in bytes (100MB)")
    max_decompressed_size: int = Field(default=500 * 1024 * 1024, gt=0, description="Max decompressed size in bytes (500MB)")


class PoolSettings(BaseModel):
    """Connection pool configuration from environment."""

    pool_connections: int = Field(default=10, ge=1, description="Connection pool size")
    pool_maxsize: int = Field(default=10, ge=1, description="Max connections per host")
    max_redirects: int = Field(default=5, ge=0, description="Maximum redirects")


class LoggingSettings(BaseModel):
    """Logging configuration from environment."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
    format: Literal["json", "text", "colored"] = Field(default="text")
    enable_console: bool = Field(default=True)
    enable_file: bool = Field(default=False)
    file_path: Optional[str] = None
    max_bytes: int = Field(default=10 * 1024 * 1024, gt=0, description="10MB")
    backup_count: int = Field(default=5, ge=0)
    enable_correlation_id: bool = Field(default=True)

    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v: Optional[str], info) -> Optional[str]:
        """Validate file_path is required when enable_file=True."""
        if info.data.get('enable_file') and not v:
            raise ValueError("file_path is required when enable_file=True")
        return v


class HTTPClientSettings(BaseSettings):
    """
    Main HTTP Client configuration from environment variables.

    Reads from:
    1. Environment variables (HTTP_CLIENT_*)
    2. .env file
    3. Defaults

    Example .env file:
        HTTP_CLIENT_BASE_URL=https://api.example.com
        HTTP_CLIENT_TIMEOUT_CONNECT=5.0
        HTTP_CLIENT_TIMEOUT_READ=10.0
        HTTP_CLIENT_RETRY_MAX_ATTEMPTS=3
        HTTP_CLIENT_LOG_LEVEL=INFO
        HTTP_CLIENT_LOG_FILE_PATH=/var/log/app.log
        HTTP_CLIENT_API_KEY=secret-key-123

    Usage:
        >>> settings = HTTPClientSettings()
        >>> print(settings.base_url)
        'https://api.example.com'
    """

    model_config = SettingsConfigDict(
        env_prefix='HTTP_CLIENT_',
        env_nested_delimiter='_',
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )

    # Base configuration
    base_url: str = Field(default="", description="Base URL for all requests")

    # Timeouts (flat structure for env vars)
    timeout_connect: float = Field(default=5.0, gt=0)
    timeout_read: float = Field(default=10.0, gt=0)
    timeout_total: Optional[float] = Field(default=30.0, gt=0)

    # Retry
    retry_max_attempts: int = Field(default=3, ge=1, le=10)
    retry_backoff_factor: float = Field(default=2.0, ge=1.0)
    retry_backoff_jitter: bool = Field(default=True)
    retry_backoff_max: float = Field(default=60.0, gt=0)

    # Security
    security_verify_ssl: bool = Field(default=True)
    security_max_response_size: int = Field(default=100 * 1024 * 1024, gt=0)
    security_max_decompressed_size: int = Field(default=500 * 1024 * 1024, gt=0)

    # Connection pool
    pool_connections: int = Field(default=10, ge=1)
    pool_maxsize: int = Field(default=10, ge=1)
    pool_max_redirects: int = Field(default=5, ge=0)

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
    log_format: Literal["json", "text", "colored"] = Field(default="text")
    log_enable_console: bool = Field(default=True)
    log_enable_file: bool = Field(default=False)
    log_file_path: Optional[str] = None
    log_max_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    log_backup_count: int = Field(default=5, ge=0)
    log_enable_correlation_id: bool = Field(default=True)

    # Secrets (will be masked in logs)
    api_key: Optional[str] = Field(default=None, description="API key for authentication")
    api_secret: Optional[str] = Field(default=None, description="API secret for authentication")

    @field_validator('api_key', 'api_secret')
    @classmethod
    def validate_secret_length(cls, v: Optional[str]) -> Optional[str]:
        """Validate secret is not too short."""
        if v is not None and len(v) < 8:
            raise ValueError("Secret must be at least 8 characters")
        return v

    def to_timeout_settings(self) -> TimeoutSettings:
        """Convert to TimeoutSettings."""
        return TimeoutSettings(
            connect=self.timeout_connect,
            read=self.timeout_read,
            total=self.timeout_total,
        )

    def to_retry_settings(self) -> RetrySettings:
        """Convert to RetrySettings."""
        return RetrySettings(
            max_attempts=self.retry_max_attempts,
            backoff_factor=self.retry_backoff_factor,
            backoff_jitter=self.retry_backoff_jitter,
            backoff_max=self.retry_backoff_max,
        )

    def to_security_settings(self) -> SecuritySettings:
        """Convert to SecuritySettings."""
        return SecuritySettings(
            verify_ssl=self.security_verify_ssl,
            max_response_size=self.security_max_response_size,
            max_decompressed_size=self.security_max_decompressed_size,
        )

    def to_pool_settings(self) -> PoolSettings:
        """Convert to PoolSettings."""
        return PoolSettings(
            pool_connections=self.pool_connections,
            pool_maxsize=self.pool_maxsize,
            max_redirects=self.pool_max_redirects,
        )

    def to_logging_settings(self) -> Optional[LoggingSettings]:
        """Convert to LoggingSettings if logging enabled."""
        if not self.log_enable_file and not self.log_enable_console:
            return None

        return LoggingSettings(
            level=self.log_level,
            format=self.log_format,
            enable_console=self.log_enable_console,
            enable_file=self.log_enable_file,
            file_path=self.log_file_path,
            max_bytes=self.log_max_bytes,
            backup_count=self.log_backup_count,
            enable_correlation_id=self.log_enable_correlation_id,
        )
