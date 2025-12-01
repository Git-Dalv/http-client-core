"""
Система конфигурации для HTTP Client.

Все конфиги immutable (frozen dataclasses) для потокобезопасности.
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict, Set, Union

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
        verify_ssl: Проверять SSL сертификаты
        allow_redirects: Разрешать редиректы

    Examples:
        >>> SecurityConfig(max_response_size=50*1024*1024)  # 50MB
        >>> SecurityConfig(verify_ssl=False)  # Для тестов
    """
    max_response_size: int = 100 * 1024 * 1024  # 100MB
    max_decompressed_size: int = 500 * 1024 * 1024  # 500MB
    verify_ssl: bool = True
    allow_redirects: bool = True

    def __post_init__(self):
        """Валидация."""
        if self.max_response_size <= 0:
            raise ValueError("max_response_size must be positive")
        if self.max_decompressed_size <= 0:
            raise ValueError("max_decompressed_size must be positive")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
    headers: Dict[str, str] = field(default_factory=dict)
    proxies: Dict[str, str] = field(default_factory=dict)

    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    pool: ConnectionPoolConfig = field(default_factory=ConnectionPoolConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)

    def __post_init__(self):
        """Normalize base_url by removing trailing slashes."""
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

        # Security конфигурация
        security_cfg = SecurityConfig(verify_ssl=verify_ssl)

        return cls(
            base_url=base_url,
            headers=headers or {},
            proxies=proxies or {},
            timeout=timeout_cfg,
            retry=retry_cfg,
            security=security_cfg,
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
            security=self.security
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
            security=self.security
        )
