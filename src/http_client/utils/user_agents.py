"""
User-Agent строки и генератор для имитации реальных браузеров.

Содержит базу актуальных User-Agent строк для популярных браузеров
и операционных систем с возможностью случайного выбора или генерации.
"""

import random
from typing import List, Optional, Literal
from dataclasses import dataclass


BrowserType = Literal["chrome", "firefox", "safari", "edge", "opera"]
OSType = Literal["windows", "macos", "linux", "android", "ios"]


@dataclass
class UserAgentInfo:
    """Информация о User-Agent строке"""

    ua_string: str
    browser: BrowserType
    os: OSType
    popularity: float  # 0.0 - 1.0, для weighted выбора


# ==================== БАЗА USER-AGENT СТРОК ====================

# Chrome на различных ОС (самый популярный браузер)
CHROME_USER_AGENTS: List[UserAgentInfo] = [
    # Windows
    UserAgentInfo(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "chrome", "windows", 0.95
    ),
    UserAgentInfo(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "chrome", "windows", 0.90
    ),
    UserAgentInfo(
        "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "chrome", "windows", 0.85
    ),

    # macOS
    UserAgentInfo(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "chrome", "macos", 0.80
    ),
    UserAgentInfo(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "chrome", "macos", 0.75
    ),

    # Linux
    UserAgentInfo(
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "chrome", "linux", 0.70
    ),
    UserAgentInfo(
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "chrome", "linux", 0.65
    ),

    # Android
    UserAgentInfo(
        "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "chrome", "android", 0.60
    ),
    UserAgentInfo(
        "Mozilla/5.0 (Linux; Android 12; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
        "chrome", "android", 0.55
    ),
]

# Firefox на различных ОС
FIREFOX_USER_AGENTS: List[UserAgentInfo] = [
    # Windows
    UserAgentInfo(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "firefox", "windows", 0.50
    ),
    UserAgentInfo(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "firefox", "windows", 0.45
    ),

    # macOS
    UserAgentInfo(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "firefox", "macos", 0.40
    ),
    UserAgentInfo(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13.6; rv:120.0) Gecko/20100101 Firefox/120.0",
        "firefox", "macos", 0.35
    ),

    # Linux
    UserAgentInfo(
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "firefox", "linux", 0.30
    ),
    UserAgentInfo(
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "firefox", "linux", 0.25
    ),

    # Android
    UserAgentInfo(
        "Mozilla/5.0 (Android 13; Mobile; rv:121.0) Gecko/121.0 Firefox/121.0",
        "firefox", "android", 0.20
    ),
]

# Safari (только macOS и iOS)
SAFARI_USER_AGENTS: List[UserAgentInfo] = [
    # macOS
    UserAgentInfo(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "safari", "macos", 0.70
    ),
    UserAgentInfo(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "safari", "macos", 0.65
    ),

    # iOS
    UserAgentInfo(
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "safari", "ios", 0.60
    ),
    UserAgentInfo(
        "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "safari", "ios", 0.55
    ),
]

# Edge (Chromium-based)
EDGE_USER_AGENTS: List[UserAgentInfo] = [
    # Windows
    UserAgentInfo(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "edge", "windows", 0.50
    ),
    UserAgentInfo(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        "edge", "windows", 0.45
    ),

    # macOS
    UserAgentInfo(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "edge", "macos", 0.40
    ),
]

# Opera
OPERA_USER_AGENTS: List[UserAgentInfo] = [
    # Windows
    UserAgentInfo(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/105.0.0.0",
        "opera", "windows", 0.30
    ),

    # macOS
    UserAgentInfo(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/105.0.0.0",
        "opera", "macos", 0.25
    ),
]


# Объединенный список всех User-Agent
ALL_USER_AGENTS: List[UserAgentInfo] = (
        CHROME_USER_AGENTS
        + FIREFOX_USER_AGENTS
        + SAFARI_USER_AGENTS
        + EDGE_USER_AGENTS
        + OPERA_USER_AGENTS
)


# ==================== ГЕНЕРАТОР USER-AGENT ====================

class UserAgentGenerator:
    """
    Генератор User-Agent строк с различными стратегиями выбора.

    Example:
        # Случайный выбор
        generator = UserAgentGenerator()
        ua = generator.random()

        # Только Chrome на Windows
        ua = generator.random(browser="chrome", os="windows")

        # Weighted выбор (популярные UA чаще)
        ua = generator.weighted_random()

        # Последовательная ротация
        ua = generator.next()
    """

    def __init__(
            self,
            user_agents: Optional[List[UserAgentInfo]] = None,
            browser: Optional[BrowserType] = None,
            os: Optional[OSType] = None,
    ):
        """
        Инициализация генератора.

        Args:
            user_agents: Список UserAgentInfo (по умолчанию ALL_USER_AGENTS)
            browser: Фильтр по браузеру (None = все)
            os: Фильтр по ОС (None = все)
        """
        self._user_agents = user_agents or ALL_USER_AGENTS
        self._browser_filter = browser
        self._os_filter = os
        self._current_index = 0

        # Применяем фильтры
        self._filtered_agents = self._apply_filters()

        if not self._filtered_agents:
            raise ValueError(
                f"No user agents found for browser={browser}, os={os}"
            )

    def _apply_filters(self) -> List[UserAgentInfo]:
        """Применяет фильтры по браузеру и ОС"""
        filtered = self._user_agents

        if self._browser_filter:
            filtered = [ua for ua in filtered if ua.browser == self._browser_filter]

        if self._os_filter:
            filtered = [ua for ua in filtered if ua.os == self._os_filter]

        return filtered

    def random(
            self,
            browser: Optional[BrowserType] = None,
            os: Optional[OSType] = None,
    ) -> str:
        """
        Возвращает случайный User-Agent.

        Args:
            browser: Фильтр по браузеру (переопределяет конструктор)
            os: Фильтр по ОС (переопределяет конструктор)

        Returns:
            User-Agent строка

        Example:
            ua = generator.random()
            ua = generator.random(browser="chrome")
            ua = generator.random(browser="firefox", os="linux")
        """
        # Временные фильтры для этого вызова
        if browser or os:
            temp_agents = self._user_agents
            if browser:
                temp_agents = [ua for ua in temp_agents if ua.browser == browser]
            if os:
                temp_agents = [ua for ua in temp_agents if ua.os == os]

            if not temp_agents:
                raise ValueError(f"No user agents found for browser={browser}, os={os}")

            return random.choice(temp_agents).ua_string

        return random.choice(self._filtered_agents).ua_string

    def weighted_random(
            self,
            browser: Optional[BrowserType] = None,
            os: Optional[OSType] = None,
    ) -> str:
        """
        Возвращает случайный User-Agent с учетом популярности.

        Популярные User-Agent будут выбираться чаще.

        Args:
            browser: Фильтр по браузеру
            os: Фильтр по ОС

        Returns:
            User-Agent строка

        Example:
            # Chrome на Windows будет выбираться чаще всего
            ua = generator.weighted_random()
        """
        # Временные фильтры
        if browser or os:
            temp_agents = self._user_agents
            if browser:
                temp_agents = [ua for ua in temp_agents if ua.browser == browser]
            if os:
                temp_agents = [ua for ua in temp_agents if ua.os == os]

            if not temp_agents:
                raise ValueError(f"No user agents found for browser={browser}, os={os}")

            agents = temp_agents
        else:
            agents = self._filtered_agents

        # Weighted random выбор
        weights = [ua.popularity for ua in agents]
        selected = random.choices(agents, weights=weights, k=1)[0]

        return selected.ua_string

    def next(self) -> str:
        """
        Возвращает следующий User-Agent в последовательности (round-robin).

        Полезно для последовательной ротации без повторений.

        Returns:
            User-Agent строка

        Example:
            # Последовательная ротация
            ua1 = generator.next()  # Chrome Windows
            ua2 = generator.next()  # Chrome Windows (другая версия)
            ua3 = generator.next()  # Chrome macOS
        """
        ua = self._filtered_agents[self._current_index]
        self._current_index = (self._current_index + 1) % len(self._filtered_agents)
        return ua.ua_string

    def get_all(self) -> List[str]:
        """
        Возвращает все отфильтрованные User-Agent строки.

        Returns:
            Список User-Agent строк
        """
        return [ua.ua_string for ua in self._filtered_agents]

    def reset(self):
        """Сбрасывает индекс для next() на начало"""
        self._current_index = 0


# ==================== УДОБНЫЕ ФУНКЦИИ ====================

def get_random_user_agent(
        browser: Optional[BrowserType] = None,
        os: Optional[OSType] = None,
) -> str:
    """
    Быстрая функция для получения случайного User-Agent.

    Args:
        browser: Фильтр по браузеру
        os: Фильтр по ОС

    Returns:
        User-Agent строка

    Example:
        from http_client.utils.user_agents import get_random_user_agent

        ua = get_random_user_agent()
        ua = get_random_user_agent(browser="chrome")
        ua = get_random_user_agent(browser="firefox", os="linux")
    """
    generator = UserAgentGenerator(browser=browser, os=os)
    return generator.random()


def get_chrome_user_agent(os: Optional[OSType] = None) -> str:
    """Возвращает случайный Chrome User-Agent"""
    return get_random_user_agent(browser="chrome", os=os)


def get_firefox_user_agent(os: Optional[OSType] = None) -> str:
    """Возвращает случайный Firefox User-Agent"""
    return get_random_user_agent(browser="firefox", os=os)


def get_safari_user_agent() -> str:
    """Возвращает случайный Safari User-Agent (только macOS/iOS)"""
    return get_random_user_agent(browser="safari")


def get_mobile_user_agent() -> str:
    """Возвращает случайный мобильный User-Agent (Android или iOS)"""
    mobile_agents = [
        ua for ua in ALL_USER_AGENTS
        if ua.os in ("android", "ios")
    ]
    return random.choice(mobile_agents).ua_string


# ==================== КОНСТАНТЫ ДЛЯ БЫСТРОГО ДОСТУПА ====================

# Самый популярный User-Agent (Chrome на Windows)
DEFAULT_USER_AGENT = CHROME_USER_AGENTS[0].ua_string

# Список самых популярных User-Agent (топ 5)
TOP_USER_AGENTS = [
    ua.ua_string for ua in sorted(
        ALL_USER_AGENTS,
        key=lambda x: x.popularity,
        reverse=True
    )[:5]
]