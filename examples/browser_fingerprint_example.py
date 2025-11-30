"""
Примеры использования BrowserFingerprintPlugin.

BrowserFingerprintPlugin позволяет имитировать различные браузеры,
добавляя консистентные HTTP заголовки для обхода простой защиты от ботов.
"""

from src.http_client.core.http_client import HTTPClient
from src.http_client.plugins.browser_fingerprint import BrowserFingerprintPlugin


def example_basic_chrome():
    """Пример 1: Базовое использование с Chrome."""
    print("=" * 60)
    print("Пример 1: Имитация Chrome браузера")
    print("=" * 60)

    # Создаем клиент с плагином Chrome
    client = HTTPClient(base_url="https://httpbin.org")
    chrome_plugin = BrowserFingerprintPlugin(browser="chrome")
    client.add_plugin(chrome_plugin)

    # Выполняем запрос
    response = client.get("/headers")
    headers_sent = response.json()["headers"]

    print("\nОтправленные заголовки:")
    print(f"User-Agent: {headers_sent.get('User-Agent')}")
    print(f"Accept: {headers_sent.get('Accept')}")
    print(f"Sec-Ch-Ua: {headers_sent.get('Sec-Ch-Ua')}")
    print(f"Sec-Ch-Ua-Platform: {headers_sent.get('Sec-Ch-Ua-Platform')}")

    client.close()


def example_firefox():
    """Пример 2: Использование с Firefox."""
    print("\n" + "=" * 60)
    print("Пример 2: Имитация Firefox браузера")
    print("=" * 60)

    client = HTTPClient(base_url="https://httpbin.org")
    firefox_plugin = BrowserFingerprintPlugin(browser="firefox")
    client.add_plugin(firefox_plugin)

    response = client.get("/headers")
    headers_sent = response.json()["headers"]

    print("\nОтправленные заголовки:")
    print(f"User-Agent: {headers_sent.get('User-Agent')}")
    print(f"Accept: {headers_sent.get('Accept')}")
    # Firefox не использует Client Hints
    print(f"Sec-Ch-Ua: {headers_sent.get('Sec-Ch-Ua', 'Not set (Firefox)')}")

    client.close()


def example_switch_browsers():
    """Пример 3: Переключение между браузерами."""
    print("\n" + "=" * 60)
    print("Пример 3: Переключение между браузерами")
    print("=" * 60)

    client = HTTPClient(base_url="https://httpbin.org")
    plugin = BrowserFingerprintPlugin(browser="chrome")
    client.add_plugin(plugin)

    # Запрос 1: Chrome
    print("\nЗапрос 1 (Chrome):")
    response = client.get("/headers")
    ua = response.json()["headers"]["User-Agent"]
    print(f"User-Agent: {ua[:50]}...")

    # Переключаемся на Safari
    plugin.set_browser("safari")

    # Запрос 2: Safari
    print("\nЗапрос 2 (Safari):")
    response = client.get("/headers")
    ua = response.json()["headers"]["User-Agent"]
    print(f"User-Agent: {ua[:50]}...")

    # Переключаемся на Edge
    plugin.set_browser("edge")

    # Запрос 3: Edge
    print("\nЗапрос 3 (Edge):")
    response = client.get("/headers")
    ua = response.json()["headers"]["User-Agent"]
    print(f"User-Agent: {ua[:50]}...")

    client.close()


def example_random_profiles():
    """Пример 4: Случайный выбор браузера для каждого запроса."""
    print("\n" + "=" * 60)
    print("Пример 4: Случайный браузер для каждого запроса")
    print("=" * 60)

    client = HTTPClient(base_url="https://httpbin.org")
    plugin = BrowserFingerprintPlugin(random_profile=True)
    client.add_plugin(plugin)

    print("\nВыполняем 5 запросов с случайными браузерами:")
    for i in range(5):
        response = client.get("/headers")
        ua = response.json()["headers"]["User-Agent"]

        # Определяем браузер по User-Agent
        if "Chrome" in ua and "Edg" not in ua:
            browser = "Chrome"
        elif "Firefox" in ua:
            browser = "Firefox"
        elif "Safari" in ua and "Chrome" not in ua:
            browser = "Safari"
        elif "Edg" in ua:
            browser = "Edge"
        else:
            browser = "Unknown"

        print(f"\nЗапрос {i+1}: {browser}")
        print(f"User-Agent: {ua[:60]}...")

    client.close()


def example_custom_headers():
    """Пример 5: Комбинирование с пользовательскими заголовками."""
    print("\n" + "=" * 60)
    print("Пример 5: Комбинирование с пользовательскими заголовками")
    print("=" * 60)

    client = HTTPClient(base_url="https://httpbin.org")
    plugin = BrowserFingerprintPlugin(browser="chrome")
    client.add_plugin(plugin)

    # Отправляем запрос с дополнительными заголовками
    response = client.get(
        "/headers",
        headers={
            "X-Custom-Header": "MyValue",
            "Authorization": "Bearer token123",
            # User-Agent НЕ будет перезаписан, если мы его укажем
            "User-Agent": "MyCustomUserAgent/1.0",
        },
    )

    headers_sent = response.json()["headers"]

    print("\nОтправленные заголовки:")
    print(f"User-Agent: {headers_sent.get('User-Agent')}")  # Наш кастомный
    print(f"X-Custom-Header: {headers_sent.get('X-Custom-Header')}")
    print(f"Authorization: {headers_sent.get('Authorization')}")
    print(f"Accept: {headers_sent.get('Accept')}")  # От плагина

    client.close()


def example_mobile_browser():
    """Пример 6: Имитация мобильного браузера."""
    print("\n" + "=" * 60)
    print("Пример 6: Имитация мобильного Chrome")
    print("=" * 60)

    client = HTTPClient(base_url="https://httpbin.org")
    mobile_plugin = BrowserFingerprintPlugin(browser="chrome_mobile")
    client.add_plugin(mobile_plugin)

    response = client.get("/headers")
    headers_sent = response.json()["headers"]

    print("\nОтправленные заголовки:")
    print(f"User-Agent: {headers_sent.get('User-Agent')}")
    print(f"Sec-Ch-Ua-Mobile: {headers_sent.get('Sec-Ch-Ua-Mobile')}")
    print(f"Sec-Ch-Ua-Platform: {headers_sent.get('Sec-Ch-Ua-Platform')}")

    client.close()


def example_list_available_browsers():
    """Пример 7: Список доступных браузеров."""
    print("\n" + "=" * 60)
    print("Пример 7: Список доступных браузеров")
    print("=" * 60)

    browsers = BrowserFingerprintPlugin.get_available_browsers()

    print("\nДоступные браузеры для имитации:")
    for browser in browsers:
        print(f"  - {browser}")

    print("\nПример использования каждого:")
    for browser in browsers:
        plugin = BrowserFingerprintPlugin(browser=browser)
        headers = plugin.generate_headers()
        print(f"\n{browser}:")
        print(f"  User-Agent: {headers['User-Agent'][:60]}...")


def example_web_scraping():
    """Пример 8: Использование для веб-скрапинга."""
    print("\n" + "=" * 60)
    print("Пример 8: Web Scraping с имитацией браузера")
    print("=" * 60)

    # Создаем клиент для скрапинга с имитацией Chrome
    client = HTTPClient()
    client.add_plugin(BrowserFingerprintPlugin(browser="chrome"))

    # Пример запроса к API (в реальности это может быть любой сайт)
    print("\nЗапрос к API с заголовками Chrome...")
    response = client.get("https://httpbin.org/user-agent")
    print(f"Сервер видит User-Agent: {response.json()['user-agent']}")

    # Переключаемся на случайные профили для обхода rate limiting
    print("\nПереключаемся на случайные профили...")
    plugin = client._plugins[0]  # Получаем наш плагин
    plugin.enable_random_profile()

    print("Выполняем несколько запросов с разными браузерами:")
    for i in range(3):
        response = client.get("https://httpbin.org/user-agent")
        ua = response.json()["user-agent"]
        print(f"  Запрос {i+1}: {ua[:50]}...")

    client.close()


def main():
    """Запуск всех примеров."""
    try:
        example_basic_chrome()
        example_firefox()
        example_switch_browsers()
        example_random_profiles()
        example_custom_headers()
        example_mobile_browser()
        example_list_available_browsers()
        example_web_scraping()

        print("\n" + "=" * 60)
        print("Все примеры выполнены успешно!")
        print("=" * 60)

    except Exception as e:
        print(f"\nОшибка при выполнении примеров: {e}")
        print("Убедитесь, что у вас есть доступ к интернету.")


if __name__ == "__main__":
    main()
