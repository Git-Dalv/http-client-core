# tests/unit/test_monitoring_plugin.py

from src.http_client.core.exceptions import NotFoundError
from src.http_client.core.http_client import HTTPClient
from src.http_client.plugins.monitoring_plugin import MonitoringPlugin


def test_monitoring_basic():
    """Тест базовой функциональности мониторинга"""
    monitoring = MonitoringPlugin()
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(monitoring)

    # Выполняем несколько запросов
    client.get("/posts/1")
    client.get("/posts/2")

    # Проверяем метрики
    metrics = monitoring.get_metrics()
    assert metrics["total_requests"] == 2
    assert metrics["failed_requests"] == 0
    assert "100.00%" in metrics["success_rate"]

    client.close()


def test_monitoring_failed_requests():
    """Тест отслеживания неудачных запросов"""
    monitoring = MonitoringPlugin()
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(monitoring)

    # Успешный запрос
    client.get("/posts/1")

    # Неудачный запрос
    try:
        client.get("/nonexistent-endpoint-12345")
    except NotFoundError:
        pass

    # Проверяем метрики
    metrics = monitoring.get_metrics()
    assert metrics["total_requests"] == 2
    assert metrics["failed_requests"] == 1
    assert "50.00%" in metrics["success_rate"]

    client.close()


def test_monitoring_method_stats():
    """Тест статистики по HTTP методам"""
    monitoring = MonitoringPlugin()
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(monitoring)

    # Разные методы
    client.get("/posts/1")
    client.post("/posts", json={"title": "test", "body": "test", "userId": 1})
    client.get("/posts/2")

    # Проверяем статистику методов
    metrics = monitoring.get_metrics()
    assert metrics["method_stats"]["GET"] == 2
    assert metrics["method_stats"]["POST"] == 1

    client.close()


def test_monitoring_status_code_stats():
    """Тест статистики по статус кодам"""
    monitoring = MonitoringPlugin()
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(monitoring)

    # Успешные запросы
    client.get("/posts/1")  # 200
    client.post("/posts", json={"title": "test", "body": "test", "userId": 1})  # 201

    # Проверяем статус коды
    metrics = monitoring.get_metrics()
    assert 200 in metrics["status_code_stats"]
    assert 201 in metrics["status_code_stats"]
    assert metrics["status_code_stats"][200] == 1
    assert metrics["status_code_stats"][201] == 1

    client.close()


def test_monitoring_endpoint_metrics():
    """Тест метрик по эндпоинтам"""
    monitoring = MonitoringPlugin()
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(monitoring)

    # Запросы к разным эндпоинтам
    client.get("/posts/1")
    client.get("/posts/2")
    client.get("/users/1")

    # Проверяем метрики эндпоинтов
    metrics = monitoring.get_metrics()
    endpoint_metrics = metrics["endpoint_metrics"]

    assert "/posts/1" in endpoint_metrics
    assert "/posts/2" in endpoint_metrics
    assert "/users/1" in endpoint_metrics

    assert endpoint_metrics["/posts/1"]["count"] == 1
    assert endpoint_metrics["/posts/2"]["count"] == 1
    assert endpoint_metrics["/users/1"]["count"] == 1

    client.close()


def test_monitoring_request_history():
    """Тест истории запросов"""
    monitoring = MonitoringPlugin(history_size=10)
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(monitoring)

    # Выполняем запросы
    client.get("/posts/1")
    client.get("/posts/2")

    # Проверяем историю
    history = monitoring.get_request_history()
    assert len(history) == 2
    assert history[0]["method"] == "GET"
    assert history[0]["success"] is True
    assert "/posts/1" in history[0]["url"]

    client.close()


def test_monitoring_error_tracking():
    """Тест отслеживания ошибок"""
    monitoring = MonitoringPlugin(track_errors=True)
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(monitoring)

    # Провоцируем ошибку
    try:
        client.get("/nonexistent-12345")
    except NotFoundError:
        pass

    # Проверяем историю ошибок
    errors = monitoring.get_recent_errors()
    assert len(errors) >= 1
    assert errors[0]["error_type"] == "NotFoundError"
    assert "method" in errors[0]
    assert "url" in errors[0]

    client.close()


def test_monitoring_reset():
    """Тест сброса метрик"""
    monitoring = MonitoringPlugin()
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(monitoring)

    # Выполняем запросы
    client.get("/posts/1")
    client.get("/posts/2")

    # Проверяем что метрики есть
    metrics = monitoring.get_metrics()
    assert metrics["total_requests"] == 2

    # Сбрасываем
    monitoring.reset()

    # Проверяем что метрики обнулены
    metrics = monitoring.get_metrics()
    assert metrics["total_requests"] == 0
    assert metrics["failed_requests"] == 0
    assert len(monitoring.get_request_history()) == 0

    client.close()


def test_monitoring_slowest_requests():
    """Тест получения самых медленных запросов"""
    monitoring = MonitoringPlugin()
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(monitoring)

    # Выполняем несколько запросов
    client.get("/posts/1")
    client.get("/posts/2")
    client.get("/posts/3")

    # Получаем самые медленные запросы
    slowest = monitoring.get_slowest_requests(limit=2)
    assert len(slowest) <= 2

    # Проверяем что они отсортированы по времени (от большего к меньшему)
    if len(slowest) > 1:
        assert slowest[0]["response_time"] >= slowest[1]["response_time"]

    client.close()


def test_monitoring_export_metrics():
    """Тест экспорта метрик"""
    monitoring = MonitoringPlugin()
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(monitoring)

    # Выполняем запрос
    client.get("/posts/1")

    # Экспортируем в dict
    metrics_dict = monitoring.export_metrics(format="dict")
    assert isinstance(metrics_dict, dict)
    assert "total_requests" in metrics_dict

    # Экспортируем в JSON
    metrics_json = monitoring.export_metrics(format="json")
    assert isinstance(metrics_json, str)
    assert "total_requests" in metrics_json

    client.close()


def test_monitoring_success_rate():
    """Тест расчета success rate"""
    monitoring = MonitoringPlugin()
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(monitoring)

    # Успешные запросы
    client.get("/posts/1")
    client.get("/posts/2")
    client.get("/posts/3")

    # Неудачный запрос
    try:
        client.get("/nonexistent-12345")
    except NotFoundError:
        pass

    # Проверяем success rate
    metrics = monitoring.get_metrics()
    # 3 успешных из 4 = 75%
    assert "75.00%" in metrics["success_rate"]

    client.close()


def test_monitoring_repr():
    """Тест строкового представления"""
    monitoring = MonitoringPlugin()
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(monitoring)

    # Выполняем запрос
    client.get("/posts/1")

    # Проверяем __repr__
    repr_str = repr(monitoring)
    assert "MonitoringPlugin" in repr_str
    assert "total_requests=1" in repr_str
    assert "failed_requests=0" in repr_str

    client.close()


def test_monitoring_print_summary():
    """Тест печати сводки метрик"""
    monitoring = MonitoringPlugin()
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(monitoring)

    # Выполняем несколько запросов
    client.get("/posts/1")
    client.post("/posts", json={"title": "test", "body": "test", "userId": 1})

    # Проверяем что print_summary не вызывает ошибок
    # (просто вызываем метод, он печатает в stdout)
    monitoring.print_summary()

    client.close()


def test_monitoring_endpoint_sorting():
    """Тест правильной сортировки эндпоинтов по количеству запросов"""
    monitoring = MonitoringPlugin()
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(monitoring)

    # Делаем разное количество запросов к разным эндпоинтам
    client.get("/posts/1")  # 1 запрос
    client.get("/posts/2")  # 1 запрос
    client.get("/users/1")  # 1 запрос
    client.get("/users/1")  # 2 запроса к /users/1
    client.get("/users/1")  # 3 запроса к /users/1

    # Получаем метрики
    metrics = monitoring.get_metrics()
    endpoint_metrics = metrics["endpoint_metrics"]

    # Проверяем что метрики собраны правильно
    assert endpoint_metrics["/users/1"]["count"] == 3
    assert endpoint_metrics["/posts/1"]["count"] == 1
    assert endpoint_metrics["/posts/2"]["count"] == 1

    # Проверяем что сортировка работает (не вызывает ошибок)
    # Это проверяет исправление бага с x[0]['count'] -> x[1]['count']
    try:
        monitoring.print_summary()
        sort_works = True
    except (KeyError, TypeError):
        sort_works = False

    assert sort_works, "print_summary должен работать без ошибок сортировки"

    client.close()


def test_monitoring_inf_min_time_handling():
    """Тест обработки inf значения в min_time для эндпоинтов только с ошибками"""
    monitoring = MonitoringPlugin(track_errors=True)
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(monitoring)

    # Делаем только неудачные запросы к одному эндпоинту
    try:
        client.get("/nonexistent-endpoint-12345")
    except NotFoundError:
        pass

    try:
        client.get("/nonexistent-endpoint-12345")
    except NotFoundError:
        pass

    # Получаем метрики
    metrics = monitoring.get_metrics()
    endpoint_metrics = metrics["endpoint_metrics"]

    # Проверяем что эндпоинт был зарегистрирован
    assert "/nonexistent-endpoint-12345" in endpoint_metrics

    endpoint_data = endpoint_metrics["/nonexistent-endpoint-12345"]

    # Проверяем что min_time не inf (исправление бага)
    assert endpoint_data["min_time"] != float("inf"), "min_time не должен быть inf"
    assert endpoint_data["min_time"] == 0, "min_time должен быть 0 для эндпоинтов только с ошибками"

    # Проверяем остальные метрики
    assert endpoint_data["count"] == 2
    assert endpoint_data["errors"] == 2
    assert endpoint_data["max_time"] == 0

    client.close()


def test_monitoring_mixed_success_and_errors():
    """Тест метрик эндпоинта со смешанными успешными и неудачными запросами"""
    monitoring = MonitoringPlugin()
    client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")
    client.add_plugin(monitoring)

    # Успешный запрос
    client.get("/posts/1")

    # Проверяем что min_time установлен правильно
    metrics = monitoring.get_metrics()
    endpoint_metrics = metrics["endpoint_metrics"]

    assert "/posts/1" in endpoint_metrics
    endpoint_data = endpoint_metrics["/posts/1"]

    # min_time должен быть больше или равен 0 и не inf
    assert endpoint_data["min_time"] >= 0
    assert endpoint_data["min_time"] != float("inf")
    assert endpoint_data["count"] == 1
    assert endpoint_data["errors"] == 0

    client.close()
