"""
Система конфигурации для HTTP Client.

Все конфиги immutable (frozen dataclasses) для потокобезопасности.
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict, Set, Union, Type, TYPE_CHECKING, Mapping
from types import MappingProxyType

if TYPE_CHECKING:
    from .logging import LoggingConfig

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TIMEOUT CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass(frozen=True)
class TimeoutConfig:
    """
    Конфигурация таймаутов.

    Args:
        connect: Таймаут подключения (сек)
        read: Таймаут чтения данных (сек)
        total: Общий лимит времени запроса (опционально)

    Examples:
        >>> TimeoutConfig(connect=5, read=30)
        >>> TimeoutConfig(connect=3, read=60, total=90)
    """
    connect: int = 5
    read: int = 30
    total: Optional[int] = None

    def __post_init__(self):
        """Валидация."""
        if self.connect <= 0:
            raise ValueError("connect timeout must be positive")
        if self.read <= 0:
            raise ValueError("read timeout must be positive")
        if self.total is not None and self.total <= 0:
            raise ValueError("total timeout must be positive")

    def as_tuple(self) -> Tuple[int, int]:
        """Вернуть как (connect, read) для requests."""
        return (self.connect, self.read)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RETRY CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass(frozen=True)
class RetryConfig:
    """
    Конфигурация retry стратегии.

    Args:
        max_attempts: Максимум попыток (включая первую)
        backoff_base: Базовая задержка (сек)
        backoff_factor: Множитель для exponential backoff
        backoff_max: Максимальная задержка (сек)
        backoff_jitter: Добавлять случайность (против thundering herd)
        idempotent_methods: Какие HTTP методы можно ретраить
        retryable_status_codes: Какие статус коды ретраить
        respect_retry_after: Учитывать Retry-After header
        retry_after_max: Максимум ждать из Retry-After (сек)

    Examples:
        >>> RetryConfig(max_attempts=3, backoff_base=0.5)
        >>> RetryConfig(max_attempts=5, backoff_max=120)
    """
    max_attempts: int = 3
    backoff_base: float = 0.5
    backoff_factor: float = 2.0
    backoff_max: float = 60.0
    backoff_jitter: bool = True

    idempotent_methods: Set[str] = field(
        default_factory=lambda: {'GET', 'HEAD', 'PUT', 'DELETE', 'OPTIONS', 'TRACE'}
    )

    retryable_status_codes: Set[int] = field(
        default_factory=lambda: {408, 429, 500, 502, 503, 504}
    )

    respect_retry_after: bool = True
    retry_after_max: int = 300  # 5 минут

    def __post_init__(self):
        """Валидация."""
        if self.max_attempts < 0:
            raise ValueError("max_attempts must be non-negative")
        if self.backoff_base < 0:
            raise ValueError("backoff_base must be non-negative")
        if self.backoff_factor < 1:
            raise ValueError("backoff_factor must be >= 1")
        if self.backoff_max < 0:
            raise ValueError("backoff_max must be non-negative")
        if self.retry_after_max < 0:
            raise ValueError("retry_after_max must be non-negative")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONNECTION POOL CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass(frozen=True)
class ConnectionPoolConfig:
    """
    Конфигурация connection pool.

    Args:
        pool_connections: Количество connection pools для кеширования
        pool_maxsize: Максимум соединений в пуле
        pool_block: Блокировать при достижении лимита
        max_redirects: Максимум редиректов

    Examples:
        >>> ConnectionPoolConfig(pool_maxsize=20)
        >>> ConnectionPoolConfig(pool_connections=10, pool_maxsize=10)
    """
    pool_connections: int = 10
    pool_maxsize: int = 10
    pool_block: bool = False
    max_redirects: int = 30

    def __post_init__(self):
        """Валидация."""
        if self.pool_connections <= 0:
            raise ValueError("pool_connections must be positive")
        if self.pool_maxsize <= 0:
            raise ValueError("pool_maxsize must be positive")
        if self.max_redirects < 0:
            raise ValueError("max_redirects must be non-negative")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECURITY CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass(frozen=True)
class SecurityConfig:
    """
    Конфигурация безопасности.

    Args:
        max_response_size: Максимальный размер ответа (байты)
        max_decompressed_size: Максимальный размер распакованных данных
        max_compression_ratio: Максимально допустимое соотношение сжатия (защита от decompression bomb)
        verify_ssl: Проверять SSL сертификаты
        allow_redirects: Разрешать редиректы
        sensitive_url_params: Дополнительные sensitive параметры для маскирования в логах

    Examples:
        >>> SecurityConfig(max_response_size=50*1024*1024)  # 50MB
        >>> SecurityConfig(verify_ssl=False)  # Для тестов
        >>> SecurityConfig(max_compression_ratio=10.0)  # Более строгая защита
        >>> SecurityConfig(sensitive_url_params={'custom_token', 'app_key'})
    """
    max_response_size: int = 100 * 1024 * 1024  # 100MB
    max_decompressed_size: int = 500 * 1024 * 1024  # 500MB
    max_compression_ratio: float = 20.0  # 20:1 защита от decompression bomb
    verify_ssl: bool = True
    allow_redirects: bool = True
    sensitive_url_params: Set[str] = field(default_factory=set)

    def __post_init__(self):
        """Валидация."""
        if self.max_response_size <= 0:
            raise ValueError("max_response_size must be positive")
        if self.max_decompressed_size <= 0:
            raise ValueError("max_decompressed_size must be positive")
        if self.max_compression_ratio <= 0:
            raise ValueError("max_compression_ratio must be positive")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CIRCUIT BREAKER CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass(frozen=True)
class CircuitBreakerConfig:
    """
    Конфигурация Circuit Breaker для защиты от каскадных сбоев.

    Circuit Breaker временно блокирует запросы при высоком уровне ошибок,
    предотвращая каскадные отказы и давая системе время на восстановление.

    Args:
        enabled: Включен ли Circuit Breaker (по умолчанию выключен для backward compatibility)
        failure_threshold: Количество ошибок для открытия circuit
        recovery_timeout: Время (сек) до попытки восстановления
        half_open_max_calls: Максимум пробных запросов в HALF_OPEN состоянии
        exclude_exceptions: Исключения, которые не считаются failures

    States:
        - CLOSED: нормальная работа
        - OPEN: слишком много ошибок, запросы блокируются
        - HALF_OPEN: тестирование восстановления

    Examples:
        >>> CircuitBreakerConfig(enabled=True, failure_threshold=5)
        >>> CircuitBreakerConfig(
        ...     enabled=True,
        ...     failure_threshold=10,
        ...     recovery_timeout=60.0,
        ...     exclude_exceptions=frozenset([TimeoutError])
        ... )
    """
    enabled: bool = False
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3
    exclude_exceptions: frozenset = field(default_factory=frozenset)

    def __post_init__(self):
        """Валидация."""
        if self.failure_threshold <= 0:
            raise ValueError("failure_threshold must be positive")
        if self.recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be positive")
        if self.half_open_max_calls <= 0:
            raise ValueError("half_open_max_calls must be positive")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _freeze_dict(d: Optional[Dict[str, str]]) -> Mapping[str, str]:
    """
    Convert dict to immutable MappingProxyType.

    Args:
        d: Dictionary to freeze (can be None)

    Returns:
        Immutable MappingProxyType

    Example:
        >>> frozen = _freeze_dict({"X-API-Key": "secret"})
        >>> frozen["X-New"] = "value"  # Raises TypeError
    """
    if d is None:
        return MappingProxyType({})
    return MappingProxyType(dict(d))

@dataclass(frozen=True)
class HTTPClientConfig:
    """
    Главная конфигурация HTTPClient.

    Immutable конфигурация для потокобезопасности.

    Args:
        base_url: Базовый URL (опционально)
        headers: Дефолтные заголовки
        proxies: Прокси конфигурация
        timeout: Конфигурация таймаутов
        retry: Конфигурация retry
        pool: Конфигурация connection pool
        security: Конфигурация безопасности

    Examples:
        >>> config = HTTPClientConfig(base_url="https://api.example.com")
        >>> config = HTTPClientConfig.create(timeout=60, max_retries=5)
    """
    base_url: Optional[str] = None
    headers: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    proxies: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    pool: ConnectionPoolConfig = field(default_factory=ConnectionPoolConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    logging: Optional['LoggingConfig'] = None  # Logging configuration (None = no logging)

    def __post_init__(self):
        """Normalize base_url and freeze mutable dicts."""
        # Freeze mutable dicts to ensure immutability
        if isinstance(self.headers, dict):
            object.__setattr__(self, 'headers', MappingProxyType(dict(self.headers)))
        if isinstance(self.proxies, dict):
            object.__setattr__(self, 'proxies', MappingProxyType(dict(self.proxies)))

        # Normalize base_url by removing trailing slashes
        if self.base_url:
            # Remove trailing slashes
            normalized = self.base_url.rstrip('/')
            if normalized != self.base_url:
                object.__setattr__(self, 'base_url', normalized)

    @classmethod
    def create(
        cls,
        base_url: Optional[str] = None,
        timeout: Union[int, Tuple[int, int], TimeoutConfig] = 30,
        connect_timeout: Optional[int] = None,
        read_timeout: Optional[int] = None,
        max_retries: int = 3,
        verify_ssl: bool = True,
        headers: Optional[Dict[str, str]] = None,
        proxies: Optional[Dict[str, str]] = None,
        pool_connections: Optional[int] = None,
        pool_maxsize: Optional[int] = None,
        pool_block: Optional[bool] = None,
        max_redirects: Optional[int] = None,
        logging: Optional['LoggingConfig'] = None,
        **kwargs
    ) -> 'HTTPClientConfig':
        """
        Удобный конструктор конфигурации.

        Args:
            base_url: Базовый URL
            timeout: Таймаут (int или (connect, read) или TimeoutConfig)
            connect_timeout: Таймаут подключения (переопределяет timeout)
            read_timeout: Таймаут чтения (переопределяет timeout)
            max_retries: Количество retry попыток
            verify_ssl: Проверять SSL
            headers: Заголовки
            proxies: Прокси
            pool_connections: Количество connection pool connections
            pool_maxsize: Максимальный размер connection pool
            pool_block: Блокировать ли при достижении лимита pool
            max_redirects: Максимальное количество редиректов
            logging: Конфигурация логирования (None = отключить логирование)

        Returns:
            HTTPClientConfig instance

        Examples:
            >>> config = HTTPClientConfig.create(timeout=60)
            >>> config = HTTPClientConfig.create(connect_timeout=5, read_timeout=30)
            >>> config = HTTPClientConfig.create(timeout=(5, 60), max_retries=5)
        """

        # Timeout конфигурация
        if isinstance(timeout, TimeoutConfig):
            timeout_cfg = timeout
        elif connect_timeout is not None or read_timeout is not None:
            timeout_cfg = TimeoutConfig(
                connect=connect_timeout or 5,
                read=read_timeout or 30
            )
        elif isinstance(timeout, tuple):
            timeout_cfg = TimeoutConfig(connect=timeout[0], read=timeout[1])
        else:
            timeout_cfg = TimeoutConfig(connect=5, read=timeout)

        # Retry конфигурация
        # max_retries = количество ретраев (не включая оригинальный запрос)
        # max_attempts = общее количество попыток (включая оригинальный)
        retry_cfg = RetryConfig(max_attempts=max_retries + 1)

        # Pool конфигурация
        pool_kwargs = {}
        if pool_connections is not None:
            pool_kwargs['pool_connections'] = pool_connections
        if pool_maxsize is not None:
            pool_kwargs['pool_maxsize'] = pool_maxsize
        if pool_block is not None:
            pool_kwargs['pool_block'] = pool_block
        if max_redirects is not None:
            pool_kwargs['max_redirects'] = max_redirects

        pool_cfg = ConnectionPoolConfig(**pool_kwargs) if pool_kwargs else ConnectionPoolConfig()

        # Security конфигурация
        security_cfg = SecurityConfig(verify_ssl=verify_ssl)

        return cls(
            base_url=base_url,
            headers=headers or {},
            proxies=proxies or {},
            timeout=timeout_cfg,
            retry=retry_cfg,
            pool=pool_cfg,
            security=security_cfg,
            logging=logging,
            **kwargs
        )

    def with_timeout(self, timeout: Union[int, Tuple[int, int], TimeoutConfig]) -> 'HTTPClientConfig':
        """
        Создать новый конфиг с изменённым timeout.

        Args:
            timeout: Новый таймаут

        Returns:
            Новый HTTPClientConfig

        Example:
            >>> new_config = config.with_timeout(60)
        """
        if isinstance(timeout, TimeoutConfig):
            timeout_cfg = timeout
        elif isinstance(timeout, tuple):
            timeout_cfg = TimeoutConfig(connect=timeout[0], read=timeout[1])
        else:
            timeout_cfg = TimeoutConfig(connect=5, read=timeout)

        return HTTPClientConfig(
            base_url=self.base_url,
            headers=self.headers,
            proxies=self.proxies,
            timeout=timeout_cfg,
            retry=self.retry,
            pool=self.pool,
            security=self.security,
            circuit_breaker=self.circuit_breaker,
            logging=self.logging
        )

    def with_retries(self, max_attempts: int) -> 'HTTPClientConfig':
        """
        Создать новый конфиг с изменённым retry.

        Args:
            max_attempts: Максимальное количество попыток (включая оригинальный запрос)

        Returns:
            Новый HTTPClientConfig

        Example:
            >>> new_config = config.with_retries(5)
        """
        retry_cfg = RetryConfig(max_attempts=max_attempts)

        return HTTPClientConfig(
            base_url=self.base_url,
            headers=self.headers,
            proxies=self.proxies,
            timeout=self.timeout,
            retry=retry_cfg,
            pool=self.pool,
            security=self.security,
            circuit_breaker=self.circuit_breaker,
            logging=self.logging
        )

    def with_headers(self, headers: Dict[str, str]) -> 'HTTPClientConfig':
        """
        Создать новый конфиг с дополнительными заголовками.

        Args:
            headers: Заголовки для объединения с существующими

        Returns:
            Новый HTTPClientConfig

        Example:
            >>> new_config = config.with_headers({"X-API-Key": "secret"})
        """
        # Merge existing and new headers
        merged = dict(self.headers)  # Convert MappingProxyType to dict
        merged.update(headers)

        return HTTPClientConfig(
            base_url=self.base_url,
            headers=merged,  # __post_init__ will freeze it
            proxies=self.proxies,
            timeout=self.timeout,
            retry=self.retry,
            pool=self.pool,
            security=self.security,
            circuit_breaker=self.circuit_breaker,
            logging=self.logging
        )
