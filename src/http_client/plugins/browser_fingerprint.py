"""
Browser Fingerprint Plugin - имитация отпечатков реальных браузеров.

Этот плагин генерирует консистентные HTTP заголовки, имитирующие различные
браузеры (Chrome, Firefox, Safari, Edge) для обхода простой защиты от ботов.
"""

import random
from typing import Any, Dict

import requests

from .plugin import Plugin


class BrowserProfile:
    """Профиль браузера с консистентными заголовками."""

    def __init__(
        self,
        name: str,
        user_agent: str,
        sec_ch_ua: str = None,
        sec_ch_ua_mobile: str = "?0",
        sec_ch_ua_platform: str = None,
        accept: str = None,
        accept_language: str = "en-US,en;q=0.9",
        accept_encoding: str = "gzip, deflate, br",
        upgrade_insecure_requests: str = "1",
        sec_fetch_dest: str = "document",
        sec_fetch_mode: str = "navigate",
        sec_fetch_site: str = "none",
        sec_fetch_user: str = "?1",
    ):
        """
        Инициализация профиля браузера.

        Args:
            name: Название браузера
            user_agent: User-Agent строка
            sec_ch_ua: Client Hints User-Agent (для Chromium)
            sec_ch_ua_mobile: Mobile hint
            sec_ch_ua_platform: Platform hint
            accept: Accept заголовок
            accept_language: Accept-Language заголовок
            accept_encoding: Accept-Encoding заголовок
            upgrade_insecure_requests: Upgrade-Insecure-Requests заголовок
            sec_fetch_dest: Sec-Fetch-Dest заголовок
            sec_fetch_mode: Sec-Fetch-Mode заголовок
            sec_fetch_site: Sec-Fetch-Site заголовок
            sec_fetch_user: Sec-Fetch-User заголовок
        """
        self.name = name
        self.user_agent = user_agent
        self.sec_ch_ua = sec_ch_ua
        self.sec_ch_ua_mobile = sec_ch_ua_mobile
        self.sec_ch_ua_platform = sec_ch_ua_platform
        self.accept = (
            accept
            or "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        )
        self.accept_language = accept_language
        self.accept_encoding = accept_encoding
        self.upgrade_insecure_requests = upgrade_insecure_requests
        self.sec_fetch_dest = sec_fetch_dest
        self.sec_fetch_mode = sec_fetch_mode
        self.sec_fetch_site = sec_fetch_site
        self.sec_fetch_user = sec_fetch_user

    def generate_headers(self) -> Dict[str, str]:
        """
        Генерирует заголовки для данного профиля браузера.

        Returns:
            Словарь с HTTP заголовками
        """
        headers = {
            "User-Agent": self.user_agent,
            "Accept": self.accept,
            "Accept-Language": self.accept_language,
            "Accept-Encoding": self.accept_encoding,
            "Upgrade-Insecure-Requests": self.upgrade_insecure_requests,
        }

        # Добавляем Client Hints для Chromium-based браузеров
        if self.sec_ch_ua:
            headers["Sec-CH-UA"] = self.sec_ch_ua
            headers["Sec-CH-UA-Mobile"] = self.sec_ch_ua_mobile
            if self.sec_ch_ua_platform:
                headers["Sec-CH-UA-Platform"] = self.sec_ch_ua_platform

        # Добавляем Fetch Metadata заголовки
        if self.sec_fetch_dest:
            headers["Sec-Fetch-Dest"] = self.sec_fetch_dest
        if self.sec_fetch_mode:
            headers["Sec-Fetch-Mode"] = self.sec_fetch_mode
        if self.sec_fetch_site:
            headers["Sec-Fetch-Site"] = self.sec_fetch_site
        if self.sec_fetch_user:
            headers["Sec-Fetch-User"] = self.sec_fetch_user

        return headers


# Предопределенные профили браузеров
BROWSER_PROFILES = {
    "chrome": BrowserProfile(
        name="Chrome",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        sec_ch_ua='"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        sec_ch_ua_platform='"Windows"',
        accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    ),
    "firefox": BrowserProfile(
        name="Firefox",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        sec_ch_ua=None,  # Firefox не использует Client Hints
    ),
    "safari": BrowserProfile(
        name="Safari",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        accept_language="en-US,en;q=0.9",
        sec_ch_ua=None,  # Safari не использует Client Hints
        sec_ch_ua_platform=None,
    ),
    "edge": BrowserProfile(
        name="Edge",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        sec_ch_ua='"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
        sec_ch_ua_platform='"Windows"',
        accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    ),
    "chrome_mobile": BrowserProfile(
        name="Chrome Mobile",
        user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        sec_ch_ua='"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        sec_ch_ua_mobile="?1",
        sec_ch_ua_platform='"Android"',
        accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    ),
}


class BrowserFingerprintPlugin(Plugin):
    """
    Плагин для имитации отпечатков браузера.

    Автоматически добавляет консистентные HTTP заголовки, имитирующие
    реальный браузер для обхода простой защиты от ботов.
    """

    def __init__(self, browser: str = "chrome", random_profile: bool = False):
        """
        Инициализация плагина.

        Args:
            browser: Название браузера ('chrome', 'firefox', 'safari', 'edge', 'chrome_mobile')
            random_profile: Если True, случайный браузер для каждого запроса

        Raises:
            ValueError: Если указан неизвестный браузер
        """
        if not random_profile and browser not in BROWSER_PROFILES:
            raise ValueError(
                f"Unknown browser: {browser}. Available: {', '.join(BROWSER_PROFILES.keys())}"
            )

        self.browser = browser
        self.random_profile = random_profile
        self._current_profile = None if random_profile else BROWSER_PROFILES[browser]

    def get_current_profile(self) -> BrowserProfile:
        """
        Получает текущий профиль браузера.

        Returns:
            Объект BrowserProfile
        """
        if self.random_profile:
            # Выбираем случайный профиль для каждого запроса
            browser_name = random.choice(list(BROWSER_PROFILES.keys()))
            return BROWSER_PROFILES[browser_name]
        return self._current_profile

    def generate_headers(self) -> Dict[str, str]:
        """
        Генерирует заголовки для текущего профиля.

        Returns:
            Словарь с HTTP заголовками
        """
        profile = self.get_current_profile()
        return profile.generate_headers()

    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Добавляет заголовки браузера перед запросом.

        Args:
            method: HTTP метод
            url: URL запроса
            **kwargs: Параметры запроса

        Returns:
            Обновленные параметры запроса с заголовками браузера
        """
        # Генерируем заголовки браузера
        browser_headers = self.generate_headers()

        # Объединяем с существующими заголовками (приоритет у пользовательских)
        if "headers" not in kwargs:
            kwargs["headers"] = {}

        # Добавляем заголовки браузера, не перезаписывая существующие
        for key, value in browser_headers.items():
            if key not in kwargs["headers"]:
                kwargs["headers"][key] = value

        return kwargs

    def after_response(self, response: requests.Response) -> requests.Response:
        """Обработка после получения ответа."""
        return response

    def on_error(self, error: Exception, **kwargs) -> bool:
        """Обработка ошибок."""
        return False  # Не повторять запрос

    def set_browser(self, browser: str):
        """
        Изменяет браузер для имитации.

        Args:
            browser: Название браузера

        Raises:
            ValueError: Если указан неизвестный браузер
        """
        if browser not in BROWSER_PROFILES:
            raise ValueError(
                f"Unknown browser: {browser}. Available: {', '.join(BROWSER_PROFILES.keys())}"
            )

        self.browser = browser
        self.random_profile = False
        self._current_profile = BROWSER_PROFILES[browser]

    def enable_random_profile(self):
        """Включает режим случайного выбора браузера для каждого запроса."""
        self.random_profile = True
        self._current_profile = None

    def disable_random_profile(self):
        """Отключает режим случайного выбора браузера."""
        self.random_profile = False
        self._current_profile = BROWSER_PROFILES[self.browser]

    @staticmethod
    def get_available_browsers() -> list:
        """
        Возвращает список доступных браузеров.

        Returns:
            Список названий доступных браузеров
        """
        return list(BROWSER_PROFILES.keys())
