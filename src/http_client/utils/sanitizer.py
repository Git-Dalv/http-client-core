# src/http_client/utils/sanitizer.py
"""
Утилита для маскирования чувствительных данных в логах.

Используется для защиты паролей, токенов, API ключей и других
конфиденциальных данных от попадания в логи.
"""

import re
from typing import Any, Dict, List, Union
from copy import deepcopy


# Список чувствительных полей (case-insensitive)
SENSITIVE_KEYS = {
    'password', 'passwd', 'pwd',
    'token', 'access_token', 'refresh_token', 'auth_token', 'api_token', 'bearer_token',
    'secret', 'api_secret', 'client_secret', 'secret_key',
    'api_key', 'apikey', 'key', 'private_key',
    'authorization', 'auth',
    'cookie', 'session', 'sessionid', 'session_id',
    'credit_card', 'card_number', 'cvv', 'ssn',
    'credentials', 'client_id'
}

# Регулярные выражения для обнаружения sensitive данных в строках
SENSITIVE_PATTERNS = [
    # Bearer tokens в заголовках
    (re.compile(r'(Bearer\s+)([A-Za-z0-9\-._~+/]+=*)', re.IGNORECASE), r'\1***REDACTED***'),
    # Basic auth в заголовках
    (re.compile(r'(Basic\s+)([A-Za-z0-9+/]+=*)', re.IGNORECASE), r'\1***REDACTED***'),
    # API ключи (формат: key=value или key:value)
    (re.compile(r'(api[_-]?key[\s:=]+)([^\s&,;]+)', re.IGNORECASE), r'\1***REDACTED***'),
    # Токены (формат: token=value)
    (re.compile(r'(token[\s:=]+)([^\s&,;]+)', re.IGNORECASE), r'\1***REDACTED***'),
    # Пароли (формат: password=value)
    (re.compile(r'(password[\s:=]+)([^\s&,;]+)', re.IGNORECASE), r'\1***REDACTED***'),
]


def mask_sensitive_data(data: Any, mask: str = "***REDACTED***") -> Any:
    """
    Рекурсивно маскирует чувствительные данные в словарях, списках, строках.

    Защищает от утечки паролей, токенов, API ключей и другой
    конфиденциальной информации в логах.

    Args:
        data: Данные для маскирования (dict, list, str, или любой другой тип)
        mask: Строка-заменитель для sensitive данных (по умолчанию "***REDACTED***")

    Returns:
        Копия данных с замаскированными чувствительными полями

    Examples:
        >>> headers = {"Authorization": "Bearer secret123", "Content-Type": "application/json"}
        >>> mask_sensitive_data(headers)
        {"Authorization": "***REDACTED***", "Content-Type": "application/json"}

        >>> body = {"username": "alice", "password": "secret123"}
        >>> mask_sensitive_data(body)
        {"username": "alice", "password": "***REDACTED***"}

        >>> url = "https://api.example.com?api_key=secret123&page=1"
        >>> mask_sensitive_data(url)
        "https://api.example.com?api_key=***REDACTED***&page=1"
    """
    # None, числа, булевы значения возвращаем как есть
    if data is None or isinstance(data, (bool, int, float)):
        return data

    # Строки - проверяем на sensitive паттерны
    if isinstance(data, str):
        return _mask_string(data, mask)

    # Словари - рекурсивно обрабатываем каждый ключ
    if isinstance(data, dict):
        return _mask_dict(data, mask)

    # Списки и кортежи - рекурсивно обрабатываем элементы
    if isinstance(data, (list, tuple)):
        masked_items = [mask_sensitive_data(item, mask) for item in data]
        return type(data)(masked_items)

    # Для других типов (объекты, etc) возвращаем как есть
    # (избегаем попыток сериализации сложных объектов)
    return data


def _mask_dict(data: Dict[str, Any], mask: str) -> Dict[str, Any]:
    """
    Маскирует чувствительные поля в словаре.

    Args:
        data: Словарь для обработки
        mask: Строка-заменитель

    Returns:
        Новый словарь с замаскированными значениями
    """
    result = {}

    for key, value in data.items():
        # Проверяем, является ли ключ чувствительным (case-insensitive)
        key_lower = key.lower() if isinstance(key, str) else str(key).lower()

        if _is_sensitive_key(key_lower):
            # Маскируем значение полностью
            result[key] = mask
        else:
            # Рекурсивно обрабатываем значение
            result[key] = mask_sensitive_data(value, mask)

    return result


def _mask_string(text: str, mask: str) -> str:
    """
    Маскирует чувствительные данные в строке с помощью регулярных выражений.

    Args:
        text: Строка для обработки
        mask: Строка-заменитель

    Returns:
        Строка с замаскированными чувствительными данными
    """
    result = text

    # Применяем все паттерны для поиска sensitive данных
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)

    return result


def _is_sensitive_key(key: str) -> bool:
    """
    Проверяет, является ли ключ чувствительным.

    Args:
        key: Имя ключа (в нижнем регистре)

    Returns:
        True если ключ содержит чувствительные данные
    """
    # Точное совпадение
    if key in SENSITIVE_KEYS:
        return True

    # Частичное совпадение (ключ содержит sensitive слово)
    for sensitive_key in SENSITIVE_KEYS:
        if sensitive_key in key:
            return True

    return False


def mask_url(url: str, mask: str = "***REDACTED***") -> str:
    """
    Маскирует чувствительные параметры в URL.

    Args:
        url: URL для маскирования
        mask: Строка-заменитель

    Returns:
        URL с замаскированными чувствительными параметрами

    Examples:
        >>> mask_url("https://api.example.com?api_key=secret123&page=1")
        "https://api.example.com?api_key=***REDACTED***&page=1"

        >>> mask_url("https://user:password@api.example.com/path")
        "https://user:***REDACTED***@api.example.com/path"
    """
    # Маскируем пароль в basic auth (user:password@host)
    url = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***REDACTED***@', url)

    # Маскируем чувствительные query параметры
    for sensitive_key in SENSITIVE_KEYS:
        # Формат: ?key=value или &key=value
        pattern = re.compile(
            rf'([?&]{sensitive_key}=)([^&\s]+)',
            re.IGNORECASE
        )
        url = pattern.sub(rf'\1{mask}', url)

    return url


def mask_headers(headers: Dict[str, str], mask: str = "***REDACTED***") -> Dict[str, str]:
    """
    Маскирует чувствительные заголовки HTTP.

    Специализированная функция для обработки HTTP заголовков.

    Args:
        headers: Словарь заголовков
        mask: Строка-заменитель

    Returns:
        Новый словарь заголовков с замаскированными значениями

    Examples:
        >>> headers = {"Authorization": "Bearer token123", "User-Agent": "MyApp/1.0"}
        >>> mask_headers(headers)
        {"Authorization": "***REDACTED***", "User-Agent": "MyApp/1.0"}
    """
    return _mask_dict(headers, mask)
