# src/http_client/plugins/monitoring_plugin.py

import threading
from typing import Any, Dict, List, Optional
from datetime import datetime
from collections import defaultdict
from .plugin import Plugin


class MonitoringPlugin(Plugin):
    """
    Плагин для мониторинга и сбора метрик HTTP запросов.

    Отслеживает:
    - Общее количество запросов
    - Количество неудачных запросов
    - Время ответа (среднее, мин, макс)
    - Статистику по методам HTTP
    - Статистику по статус кодам
    - Метрики по эндпоинтам
    - Историю запросов
    - Детальную информацию об ошибках

    Example:
        >>> monitoring = MonitoringPlugin()
        >>> client = HTTPClient(base_url="https://api.example.com")
        >>> client.add_plugin(monitoring)
        >>>
        >>> # Выполняем запросы
        >>> client.get("/users")
        >>> client.post("/users", json={"name": "John"})
        >>>
        >>> # Получаем метрики
        >>> metrics = monitoring.get_metrics()
        >>> print(f"Total requests: {metrics['total_requests']}")
        >>> print(f"Success rate: {metrics['success_rate']}")
        >>>
        >>> # Печатаем сводку
        >>> monitoring.print_summary()
    """

    def __init__(
            self,
            history_size: int = 100,
            track_errors: bool = True
    ):
        """
        Инициализация плагина мониторинга.

        Args:
            history_size: Максимальный размер истории запросов
            track_errors: Отслеживать ли детальную информацию об ошибках
        """
        super().__init__()

        # ВАЖНО: Инициализируем lock для потокобезопасности
        self._lock = threading.Lock()

        # Настройки
        self._history_size = history_size
        self._track_errors = track_errors

        # Счетчики
        self._total_requests = 0
        self._failed_requests = 0
        self._total_response_time = 0.0

        # Статистика
        self._method_stats: Dict[str, int] = {}
        self._status_code_stats: Dict[int, int] = {}
        self._endpoint_metrics: Dict[str, Dict[str, Any]] = {}

        # История
        self._request_history: List[Dict[str, Any]] = []
        self._error_history: List[Dict[str, Any]] = []

    def before_request(self, **kwargs: Any) -> None:
        """
        Вызывается перед отправкой запроса.
        Сохраняет время начала запроса.

        Args:
            **kwargs: Параметры запроса
        """
        # Сохраняем время начала запроса
        kwargs['_start_time'] = datetime.now()

    def after_response(self, response: Any, **kwargs: Any) -> None:
        """
        Вызывается после получения ответа.
        Собирает метрики о запросе.

        Args:
            response: Объект ответа
            **kwargs: Дополнительные параметры
        """
        with self._lock:
            # Увеличиваем счетчик запросов
            self._total_requests += 1

            # Вычисляем время ответа
            start_time = kwargs.get('_start_time')
            response_time = 0.0
            if start_time:
                response_time = (datetime.now() - start_time).total_seconds()
                self._total_response_time += response_time

            # Получаем информацию о запросе
            method = kwargs.get('method', 'GET')
            url = kwargs.get('url', '')
            status_code = response.status_code

            # Обновляем статистику по методам
            self._method_stats[method] = self._method_stats.get(method, 0) + 1

            # Обновляем статистику по статус кодам
            self._status_code_stats[status_code] = self._status_code_stats.get(status_code, 0) + 1

            # Проверяем успешность запроса
            is_success = 200 <= status_code < 400
            if not is_success:
                self._failed_requests += 1

            # Извлекаем endpoint из URL
            endpoint = self._extract_endpoint(url)

            # Обновляем метрики эндпоинта
            if endpoint not in self._endpoint_metrics:
                self._endpoint_metrics[endpoint] = {
                    'count': 0,
                    'total_time': 0,
                    'avg_time': 0,
                    'min_time': float('inf'),
                    'max_time': 0,
                    'errors': 0
                }

            metrics = self._endpoint_metrics[endpoint]
            metrics['count'] += 1
            metrics['total_time'] += response_time
            metrics['avg_time'] = metrics['total_time'] / metrics['count']
            metrics['min_time'] = min(metrics['min_time'], response_time)
            metrics['max_time'] = max(metrics['max_time'], response_time)

            if not is_success:
                metrics['errors'] += 1

            # Добавляем в историю запросов
            request_info = {
                'timestamp': datetime.now().isoformat(),
                'method': method,
                'url': url,
                'status_code': status_code,
                'response_time': response_time,
                'success': is_success
            }
            self._request_history.append(request_info)

            # Ограничиваем размер истории
            if len(self._request_history) > self._history_size:
                self._request_history.pop(0)

    # DEPRECATED: Для обратной совместимости
    def on_request(self, **kwargs: Any) -> None:
        """Устаревший метод. Используйте before_request."""
        self.before_request(**kwargs)

    # DEPRECATED: Для обратной совместимости
    def on_response(self, response: Any, **kwargs: Any) -> None:
        """Устаревший метод. Используйте after_response."""
        self.after_response(response, **kwargs)

    def on_error(self, exception: Exception, **kwargs: Any) -> None:
        """
        Обработчик ошибок - отслеживает неудачные запросы.

        Args:
            exception: Исключение которое произошло
            **kwargs: Дополнительные параметры (method, url, и т.д.)
        """
        with self._lock:
            self._total_requests += 1
            self._failed_requests += 1

            # Извлекаем информацию о запросе
            method = kwargs.get('method', 'UNKNOWN')
            url = kwargs.get('url', 'UNKNOWN')

            # Обновляем статистику по методам
            self._method_stats[method] = self._method_stats.get(method, 0) + 1

            # Получаем статус код из исключения если есть
            status_code = None
            if hasattr(exception, 'response') and exception.response is not None:
                status_code = exception.response.status_code
                self._status_code_stats[status_code] = self._status_code_stats.get(status_code, 0) + 1

            # Извлекаем endpoint из URL
            endpoint = self._extract_endpoint(url)

            # Обновляем метрики эндпоинта
            if endpoint not in self._endpoint_metrics:
                self._endpoint_metrics[endpoint] = {
                    'count': 0,
                    'total_time': 0,
                    'avg_time': 0,
                    'min_time': float('inf'),
                    'max_time': 0,
                    'errors': 0
                }

            self._endpoint_metrics[endpoint]['count'] += 1
            self._endpoint_metrics[endpoint]['errors'] += 1

            # Добавляем в историю ошибок
            if self._track_errors:
                error_info = {
                    'timestamp': datetime.now().isoformat(),
                    'method': method,
                    'url': url,
                    'error_type': type(exception).__name__,
                    'error_message': str(exception),
                    'status_code': status_code
                }
                self._error_history.append(error_info)

                # Ограничиваем размер истории ошибок
                if len(self._error_history) > self._history_size:
                    self._error_history.pop(0)

            # Добавляем в общую историю запросов
            request_info = {
                'timestamp': datetime.now().isoformat(),
                'method': method,
                'url': url,
                'status_code': status_code,
                'response_time': 0,  # Неизвестно для ошибочных запросов
                'success': False
            }
            self._request_history.append(request_info)

            # Ограничиваем размер истории
            if len(self._request_history) > self._history_size:
                self._request_history.pop(0)

    def _extract_endpoint(self, url: str) -> str:
        """
        Извлекает endpoint из полного URL.

        Args:
            url: Полный URL

        Returns:
            Endpoint (путь без домена)
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.path or '/'
        except Exception:
            return url

    def get_metrics(self) -> Dict[str, Any]:
        """
        Возвращает собранные метрики.

        Returns:
            Словарь с метриками:
            - total_requests: Общее количество запросов
            - failed_requests: Количество неудачных запросов
            - success_rate: Процент успешных запросов
            - avg_response_time: Среднее время ответа
            - method_stats: Статистика по HTTP методам
            - status_code_stats: Статистика по статус кодам
            - endpoint_metrics: Метрики по эндпоинтам
        """
        with self._lock:
            success_rate = 0.0
            if self._total_requests > 0:
                success_rate = ((self._total_requests - self._failed_requests) / self._total_requests) * 100

            avg_response_time = 0.0
            if self._total_requests > 0:
                avg_response_time = self._total_response_time / self._total_requests

            return {
                'total_requests': self._total_requests,
                'failed_requests': self._failed_requests,
                'success_rate': f'{success_rate:.2f}%',
                'avg_response_time': f'{avg_response_time:.3f}s',
                'method_stats': dict(self._method_stats),
                'status_code_stats': dict(self._status_code_stats),
                'endpoint_metrics': dict(self._endpoint_metrics)
            }

    def get_request_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Возвращает историю запросов.

        Args:
            limit: Максимальное количество записей (None = все)

        Returns:
            Список запросов с информацией о них
        """
        with self._lock:
            if limit is None:
                return list(self._request_history)
            return list(self._request_history[-limit:])

    def get_recent_errors(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Возвращает последние ошибки.

        Args:
            limit: Максимальное количество записей (None = все)

        Returns:
            Список ошибок с детальной информацией
        """
        with self._lock:
            if limit is None:
                return list(self._error_history)
            return list(self._error_history[-limit:])

    def get_slowest_requests(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Возвращает самые медленные запросы.

        Args:
            limit: Количество запросов

        Returns:
            Список самых медленных запросов
        """
        with self._lock:
            sorted_requests = sorted(
                self._request_history,
                key=lambda x: x.get('response_time', 0),
                reverse=True
            )
            return sorted_requests[:limit]

    def reset(self) -> None:
        """
        Сбрасывает все метрики и историю.
        """
        with self._lock:
            self._total_requests = 0
            self._failed_requests = 0
            self._total_response_time = 0.0
            self._method_stats.clear()
            self._status_code_stats.clear()
            self._endpoint_metrics.clear()
            self._request_history.clear()
            self._error_history.clear()

    def export_metrics(self, format: str = 'dict') -> Any:
        """
        Экспортирует метрики в указанном формате.

        Args:
            format: Формат экспорта ('dict', 'json')

        Returns:
            Метрики в указанном формате
        """
        metrics = self.get_metrics()

        if format == 'json':
            import json
            return json.dumps(metrics, indent=2)

        return metrics

    def print_summary(self) -> None:
        """
        Выводит красивую сводку метрик в консоль.
        """
        metrics = self.get_metrics()

        print("\n" + "="*60)
        print("HTTP CLIENT MONITORING SUMMARY")
        print("="*60)

        print(f"\n📊 General Statistics:")
        print(f"  Total Requests:     {metrics['total_requests']}")
        print(f"  Failed Requests:    {metrics['failed_requests']}")
        print(f"  Success Rate:       {metrics['success_rate']}")
        print(f"  Avg Response Time:  {metrics['avg_response_time']}")

        if metrics['method_stats']:
            print(f"\n🔧 Method Statistics:")
            for method, count in metrics['method_stats'].items():
                print(f"  {method:8s}: {count}")

        if metrics['status_code_stats']:
            print(f"\n📡 Status Code Statistics:")
            for code, count in sorted(metrics['status_code_stats'].items()):
                print(f"  {code}: {count}")

        if metrics['endpoint_metrics']:
            print(f"\n🎯 Top Endpoints:")
            sorted_endpoints = sorted(
                metrics['endpoint_metrics'].items(),
                key=lambda x: x[0]['count'],
                reverse=True
            )[:5]

            for endpoint, stats in sorted_endpoints:
                print(f"  {endpoint}")
                print(f"    Requests: {stats['count']}, "
                      f"Avg Time: {stats['avg_time']:.3f}s, "
                      f"Errors: {stats['errors']}")

        print("\n" + "="*60 + "\n")

    def __repr__(self) -> str:
        """Строковое представление плагина."""
        return (f"MonitoringPlugin(total_requests={self._total_requests}, "
                f"failed_requests={self._failed_requests})")