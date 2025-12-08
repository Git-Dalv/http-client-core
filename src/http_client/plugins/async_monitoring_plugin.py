# src/http_client/plugins/async_monitoring_plugin.py
"""
Async плагин для мониторинга и сбора метрик HTTP запросов.

Использует asyncio.Lock для неблокирующих операций с метриками.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List

from .async_plugin import AsyncPlugin
from .plugin import PluginPriority

logger = logging.getLogger(__name__)


class AsyncMonitoringPlugin(AsyncPlugin):
    """
    Async плагин для мониторинга HTTP запросов.

    Priority: LAST (100) - должен выполняться последним для точных метрик.

    Отслеживает:
    - Общее количество запросов
    - Количество неудачных запросов
    - Время ответа (среднее, мин, макс)
    - Статистику по статус кодам
    - Статистику по методам

    Example:
        >>> monitoring = AsyncMonitoringPlugin()
        >>> client = AsyncHTTPClient(plugins=[monitoring])
        >>>
        >>> # Выполняем запросы
        >>> await client.get("/users")
        >>> await client.post("/users", json={"name": "John"})
        >>>
        >>> # Получаем метрики
        >>> metrics = await monitoring.get_metrics()
        >>> print(f"Total requests: {metrics['total_requests']}")
    """

    priority = PluginPriority.LAST

    def __init__(self, history_size: int = 100):
        """
        Args:
            history_size: Максимальный размер истории запросов
        """
        self._history_size = history_size
        self._lock = asyncio.Lock()

        # Счетчики
        self._total_requests = 0
        self._failed_requests = 0
        self._total_response_time = 0.0
        self._min_response_time = float('inf')
        self._max_response_time = 0.0

        # Статистика
        self._method_stats: Dict[str, int] = {}
        self._status_code_stats: Dict[int, int] = {}

        # История
        self._request_history: List[Dict[str, Any]] = []

    async def before_request(
        self,
        method: str,
        url: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Сохраняет время начала запроса.
        """
        # Сохраняем время начала
        kwargs["_start_time"] = time.time()
        kwargs["_method"] = method
        kwargs["_url"] = url
        return kwargs

    async def after_response(self, response):
        """
        Собирает метрики о запросе.
        """
        # Получаем данные из request
        if not hasattr(response, 'request'):
            return response

        start_time = getattr(response.request, '_start_time', None)
        method = getattr(response.request, '_method', 'UNKNOWN')
        url = getattr(response.request, '_url', 'UNKNOWN')

        if start_time is None:
            return response

        # Вычисляем время ответа
        response_time = time.time() - start_time

        # Обновляем метрики (async)
        async with self._lock:
            self._total_requests += 1
            self._total_response_time += response_time
            self._min_response_time = min(self._min_response_time, response_time)
            self._max_response_time = max(self._max_response_time, response_time)

            # Статистика по методам
            self._method_stats[method] = self._method_stats.get(method, 0) + 1

            # Статистика по статус кодам
            status_code = response.status_code
            self._status_code_stats[status_code] = self._status_code_stats.get(status_code, 0) + 1

            # История
            self._request_history.append({
                'method': method,
                'url': url,
                'status_code': status_code,
                'response_time': response_time,
                'timestamp': time.time(),
            })

            # Ограничиваем размер истории
            if len(self._request_history) > self._history_size:
                self._request_history.pop(0)

        return response

    async def on_error(self, error: Exception, **kwargs: Any) -> None:
        """
        Отслеживает ошибки.
        """
        async with self._lock:
            self._failed_requests += 1
            self._total_requests += 1

    async def get_metrics(self) -> Dict[str, Any]:
        """
        Получить метрики.

        Returns:
            Dict с метриками:
            - total_requests: общее количество запросов
            - failed_requests: количество неудачных запросов
            - success_rate: процент успешных запросов
            - avg_response_time: среднее время ответа
            - min_response_time: минимальное время ответа
            - max_response_time: максимальное время ответа
            - method_stats: статистика по методам
            - status_code_stats: статистика по статус кодам
        """
        async with self._lock:
            successful_requests = self._total_requests - self._failed_requests
            success_rate = (successful_requests / self._total_requests * 100) if self._total_requests > 0 else 0.0
            avg_response_time = (self._total_response_time / self._total_requests) if self._total_requests > 0 else 0.0

            return {
                'total_requests': self._total_requests,
                'failed_requests': self._failed_requests,
                'successful_requests': successful_requests,
                'success_rate': round(success_rate, 2),
                'avg_response_time': round(avg_response_time, 4),
                'min_response_time': round(self._min_response_time, 4) if self._min_response_time != float('inf') else 0.0,
                'max_response_time': round(self._max_response_time, 4),
                'method_stats': dict(self._method_stats),
                'status_code_stats': dict(self._status_code_stats),
            }

    async def get_history(self) -> List[Dict[str, Any]]:
        """
        Получить историю запросов.

        Returns:
            List с записями о запросах
        """
        async with self._lock:
            return list(self._request_history)

    async def reset(self):
        """Сбросить все метрики."""
        async with self._lock:
            self._total_requests = 0
            self._failed_requests = 0
            self._total_response_time = 0.0
            self._min_response_time = float('inf')
            self._max_response_time = 0.0
            self._method_stats.clear()
            self._status_code_stats.clear()
            self._request_history.clear()
            logger.info("Monitoring metrics reset")

    async def print_summary(self):
        """Вывести сводку метрик."""
        metrics = await self.get_metrics()

        print("\n" + "=" * 50)
        print("HTTP Client Monitoring Summary")
        print("=" * 50)
        print(f"Total Requests:     {metrics['total_requests']}")
        print(f"Successful:         {metrics['successful_requests']}")
        print(f"Failed:             {metrics['failed_requests']}")
        print(f"Success Rate:       {metrics['success_rate']}%")
        print(f"\nResponse Times:")
        print(f"  Average:          {metrics['avg_response_time']:.4f}s")
        print(f"  Min:              {metrics['min_response_time']:.4f}s")
        print(f"  Max:              {metrics['max_response_time']:.4f}s")

        if metrics['method_stats']:
            print(f"\nRequests by Method:")
            for method, count in sorted(metrics['method_stats'].items()):
                print(f"  {method:8s}        {count}")

        if metrics['status_code_stats']:
            print(f"\nStatus Codes:")
            for status_code, count in sorted(metrics['status_code_stats'].items()):
                print(f"  {status_code}            {count}")

        print("=" * 50 + "\n")
