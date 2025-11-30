"""
Менеджер пула прокси с поддержкой ротации и проверки работоспособности.

Поддерживает:
- Различные типы прокси (HTTP, HTTPS, SOCKS4, SOCKS5)
- Ротацию прокси (round-robin, random, weighted)
- Проверку работоспособности прокси
- Автоматическое удаление неработающих прокси
- Статистику использования
"""

import random
import time
from typing import List, Optional, Dict, Any, Literal
from dataclasses import dataclass, field
from collections import defaultdict
import requests


ProxyType = Literal["http", "https", "socks4", "socks5"]
RotationStrategy = Literal["round_robin", "random", "weighted"]


@dataclass
class ProxyInfo:
    """Информация о прокси сервере"""

    host: str
    port: int
    proxy_type: ProxyType = "http"
    username: Optional[str] = None
    password: Optional[str] = None

    # Метрики
    success_count: int = 0
    failure_count: int = 0
    total_response_time: float = 0.0
    last_used: Optional[float] = None
    last_check: Optional[float] = None
    is_working: bool = True

    # Дополнительные метаданные
    country: Optional[str] = None
    region: Optional[str] = None
    speed: Optional[str] = None  # "fast", "medium", "slow"

    def __post_init__(self):
        """Валидация после инициализации"""
        if not self.host:
            raise ValueError("Proxy host cannot be empty")
        if not (1 <= self.port <= 65535):
            raise ValueError(f"Invalid port: {self.port}")

    @property
    def success_rate(self) -> float:
        """Процент успешных запросов (0.0 - 1.0)"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0  # Новый прокси считается рабочим
        return self.success_count / total

    @property
    def average_response_time(self) -> float:
        """Среднее время ответа в секундах"""
        if self.success_count == 0:
            return 0.0
        return self.total_response_time / self.success_count

    @property
    def url(self) -> str:
        """URL прокси для requests"""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        else:
            auth = ""

        return f"{self.proxy_type}://{auth}{self.host}:{self.port}"

    def to_dict(self) -> Dict[str, str]:
        """
        Возвращает словарь для использования в requests.

        Returns:
            {"http": "...", "https": "..."}
        """
        return {
            "http": self.url,
            "https": self.url,
        }

    def record_success(self, response_time: float):
        """Записывает успешный запрос"""
        self.success_count += 1
        self.total_response_time += response_time
        self.last_used = time.time()
        self.is_working = True

    def record_failure(self):
        """Записывает неудачный запрос"""
        self.failure_count += 1
        self.last_used = time.time()

        # Помечаем как неработающий если слишком много ошибок
        if self.success_rate < 0.3 and (self.success_count + self.failure_count) >= 5:
            self.is_working = False

    def __repr__(self) -> str:
        return (
            f"ProxyInfo({self.proxy_type}://{self.host}:{self.port}, "
            f"success_rate={self.success_rate:.2f}, "
            f"is_working={self.is_working})"
        )


class ProxyPool:
    """
    Пул прокси серверов с ротацией и мониторингом.

    Example:
        # Создание пула
        pool = ProxyPool()

        # Добавление прокси
        pool.add_proxy("proxy1.com", 8080, proxy_type="http")
        pool.add_proxy("proxy2.com", 1080, proxy_type="socks5", username="user", password="pass")

        # Получение прокси
        proxy = pool.get_proxy()

        # Использование в requests
        response = requests.get("http://example.com", proxies=proxy.to_dict())

        # Запись результата
        pool.record_success(proxy, response_time=0.5)

        # Статистика
        stats = pool.get_stats()
    """

    def __init__(
            self,
            rotation_strategy: RotationStrategy = "round_robin",
            min_success_rate: float = 0.3,
            auto_remove_failed: bool = True,
            check_on_add: bool = False,
            check_timeout: float = 5.0,
            check_url: str = "http://httpbin.org/ip",
    ):
        """
        Инициализация пула прокси.

        Args:
            rotation_strategy: Стратегия ротации прокси
            min_success_rate: Минимальный success_rate для использования (0.0-1.0)
            auto_remove_failed: Автоматически удалять неработающие прокси
            check_on_add: Проверять прокси при добавлении
            check_timeout: Таймаут для проверки прокси (секунды)
            check_url: URL для проверки работоспособности
        """
        self._proxies: List[ProxyInfo] = []
        self._rotation_strategy = rotation_strategy
        self._min_success_rate = min_success_rate
        self._auto_remove_failed = auto_remove_failed
        self._check_on_add = check_on_add
        self._check_timeout = check_timeout
        self._check_url = check_url

        self._current_index = 0
        self._total_requests = 0
        self._total_successes = 0
        self._total_failures = 0

    # ==================== Управление прокси ====================

    def add_proxy(
            self,
            host: str,
            port: int,
            proxy_type: ProxyType = "http",
            username: Optional[str] = None,
            password: Optional[str] = None,
            **metadata,
    ) -> ProxyInfo:
        """
        Добавляет прокси в пул.

        Args:
            host: Хост прокси
            port: Порт прокси
            proxy_type: Тип прокси
            username: Имя пользователя (опционально)
            password: Пароль (опционально)
            **metadata: Дополнительные метаданные (country, region, speed)

        Returns:
            Созданный ProxyInfo объект

        Raises:
            ValueError: Если прокси уже существует или невалиден

        Example:
            pool.add_proxy("proxy.com", 8080)
            pool.add_proxy("proxy.com", 1080, proxy_type="socks5", country="US")
        """
        # Создаем ProxyInfo
        proxy = ProxyInfo(
            host=host,
            port=port,
            proxy_type=proxy_type,
            username=username,
            password=password,
            **{k: v for k, v in metadata.items() if k in ["country", "region", "speed"]}
        )

        # Проверяем дубликаты
        if any(p.host == host and p.port == port for p in self._proxies):
            raise ValueError(f"Proxy {host}:{port} already exists in pool")

        # Проверяем работоспособность если включено
        if self._check_on_add:
            if not self._check_proxy(proxy):
                raise ValueError(f"Proxy {host}:{port} is not working")

        self._proxies.append(proxy)
        return proxy

    def add_proxies_from_list(
            self,
            proxies: List[str],
            proxy_type: ProxyType = "http",
            check_all: bool = False,
    ) -> int:
        """
        Добавляет несколько прокси из списка строк.

        Args:
            proxies: Список прокси в формате "host:port" или "user:pass@host:port"
            proxy_type: Тип прокси для всех
            check_all: Проверить все прокси перед добавлением

        Returns:
            Количество успешно добавленных прокси

        Example:
            proxies = [
                "proxy1.com:8080",
                "user:pass@proxy2.com:1080",
                "192.168.1.1:3128"
            ]
            count = pool.add_proxies_from_list(proxies)
        """
        added = 0

        for proxy_str in proxies:
            try:
                # Парсим строку
                if "@" in proxy_str:
                    auth, host_port = proxy_str.split("@")
                    username, password = auth.split(":")
                    host, port = host_port.split(":")
                else:
                    username = password = None
                    host, port = proxy_str.split(":")

                # Добавляем
                self.add_proxy(
                    host=host.strip(),
                    port=int(port.strip()),
                    proxy_type=proxy_type,
                    username=username,
                    password=password,
                )
                added += 1

            except Exception as e:
                # Игнорируем невалидные прокси
                continue

        # Проверяем все если нужно
        if check_all:
            self.check_all_proxies()

        return added

    def remove_proxy(self, host: str, port: int) -> bool:
        """
        Удаляет прокси из пула.

        Args:
            host: Хост прокси
            port: Порт прокси

        Returns:
            True если прокси был удален, False если не найден
        """
        for i, proxy in enumerate(self._proxies):
            if proxy.host == host and proxy.port == port:
                self._proxies.pop(i)
                return True
        return False

    def clear(self):
        """Удаляет все прокси из пула"""
        self._proxies.clear()
        self._current_index = 0

    # ==================== Получение прокси ====================

    def get_proxy(
            self,
            country: Optional[str] = None,
            proxy_type: Optional[ProxyType] = None,
    ) -> Optional[ProxyInfo]:
        """
        Возвращает прокси согласно стратегии ротации.

        Args:
            country: Фильтр по стране (опционально)
            proxy_type: Фильтр по типу (опционально)

        Returns:
            ProxyInfo объект или None если нет доступных прокси

        Example:
            proxy = pool.get_proxy()
            proxy = pool.get_proxy(country="US")
            proxy = pool.get_proxy(proxy_type="socks5")
        """
        # Фильтруем прокси
        available = self._get_available_proxies(country=country, proxy_type=proxy_type)

        if not available:
            return None

        # Выбираем согласно стратегии
        if self._rotation_strategy == "round_robin":
            proxy = self._round_robin_select(available)
        elif self._rotation_strategy == "random":
            proxy = random.choice(available)
        elif self._rotation_strategy == "weighted":
            proxy = self._weighted_select(available)
        else:
            proxy = available[0]

        return proxy

    def _get_available_proxies(
            self,
            country: Optional[str] = None,
            proxy_type: Optional[ProxyType] = None,
    ) -> List[ProxyInfo]:
        """Возвращает список доступных прокси с учетом фильтров"""
        available = [
            p for p in self._proxies
            if p.is_working and p.success_rate >= self._min_success_rate
        ]

        if country:
            available = [p for p in available if p.country == country]

        if proxy_type:
            available = [p for p in available if p.proxy_type == proxy_type]

        return available

    def _round_robin_select(self, proxies: List[ProxyInfo]) -> ProxyInfo:
        """Round-robin выбор"""
        proxy = proxies[self._current_index % len(proxies)]
        self._current_index += 1
        return proxy

    def _weighted_select(self, proxies: List[ProxyInfo]) -> ProxyInfo:
        """Weighted выбор по success_rate"""
        weights = [p.success_rate for p in proxies]
        return random.choices(proxies, weights=weights, k=1)[0]

    # ==================== Запись результатов ====================

    def record_success(self, proxy: ProxyInfo, response_time: float):
        """
        Записывает успешный запрос через прокси.

        Args:
            proxy: ProxyInfo объект
            response_time: Время ответа в секундах
        """
        proxy.record_success(response_time)
        self._total_requests += 1
        self._total_successes += 1

    def record_failure(self, proxy: ProxyInfo):
        """
        Записывает неудачный запрос через прокси.

        Args:
            proxy: ProxyInfo объект
        """
        proxy.record_failure()
        self._total_requests += 1
        self._total_failures += 1

        # Удаляем если нужно
        if self._auto_remove_failed and not proxy.is_working:
            self.remove_proxy(proxy.host, proxy.port)

    # ==================== Проверка прокси ====================

    def _check_proxy(self, proxy: ProxyInfo) -> bool:
        """
        Проверяет работоспособность прокси.

        Args:
            proxy: ProxyInfo объект

        Returns:
            True если прокси работает
        """
        try:
            start_time = time.time()
            response = requests.get(
                self._check_url,
                proxies=proxy.to_dict(),
                timeout=self._check_timeout,
            )
            response_time = time.time() - start_time

            if response.status_code == 200:
                proxy.record_success(response_time)
                proxy.last_check = time.time()
                return True
            else:
                proxy.record_failure()
                proxy.last_check = time.time()
                return False

        except Exception:
            proxy.record_failure()
            proxy.last_check = time.time()
            return False

    def check_all_proxies(self) -> Dict[str, int]:
        """
        Проверяет все прокси в пуле.

        Returns:
            Словарь с результатами: {"working": X, "failed": Y, "total": Z}

        Example:
            results = pool.check_all_proxies()
            print(f"Working: {results['working']}/{results['total']}")
        """
        working = 0
        failed = 0

        for proxy in self._proxies[:]:  # Копия списка для безопасного удаления
            if self._check_proxy(proxy):
                working += 1
            else:
                failed += 1
                if self._auto_remove_failed and not proxy.is_working:
                    self.remove_proxy(proxy.host, proxy.port)

        return {
            "working": working,
            "failed": failed,
            "total": working + failed,
        }

    # ==================== Статистика ====================

    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику пула.

        Returns:
            Словарь со статистикой
        """
        available = self._get_available_proxies()

        return {
            "total_proxies": len(self._proxies),
            "available_proxies": len(available),
            "working_proxies": sum(1 for p in self._proxies if p.is_working),
            "failed_proxies": sum(1 for p in self._proxies if not p.is_working),
            "total_requests": self._total_requests,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "overall_success_rate": (
                self._total_successes / self._total_requests
                if self._total_requests > 0 else 0.0
            ),
            "rotation_strategy": self._rotation_strategy,
        }

    def get_proxy_stats(self) -> List[Dict[str, Any]]:
        """
        Возвращает статистику по каждому прокси.

        Returns:
            Список словарей с информацией о каждом прокси
        """
        return [
            {
                "host": p.host,
                "port": p.port,
                "type": p.proxy_type,
                "is_working": p.is_working,
                "success_rate": p.success_rate,
                "success_count": p.success_count,
                "failure_count": p.failure_count,
                "avg_response_time": p.average_response_time,
                "last_used": p.last_used,
                "country": p.country,
            }
            for p in self._proxies
        ]

    # ==================== Утилиты ====================

    def __len__(self) -> int:
        """Возвращает количество прокси в пуле"""
        return len(self._proxies)

    def __bool__(self) -> bool:
        """Возвращает True если есть хотя бы один прокси"""
        return len(self._proxies) > 0

    def __repr__(self) -> str:
        available = len(self._get_available_proxies())
        return (
            f"ProxyPool(total={len(self._proxies)}, available={available}, "
            f"strategy='{self._rotation_strategy}')"
        )