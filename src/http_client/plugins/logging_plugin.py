# src/http_client/plugins/logging_plugin.py

import logging
from typing import Any, Dict

import requests

from .plugin import Plugin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LoggingPlugin(Plugin):
    """Плагин для логирования HTTP запросов и ответов"""

    def before_request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        logger.info(f"Sending {method} request to {url}")
        if kwargs.get("json"):
            logger.debug(f"Request body: {kwargs['json']}")
        if kwargs.get("params"):
            logger.debug(f"Request params: {kwargs['params']}")
        return kwargs

    def after_response(self, response: requests.Response) -> requests.Response:
        logger.info(f"Received response: {response.status_code} from {response.url}")
        logger.debug(f"Response body: {response.text[:200]}...")  # First 200 chars
        return response

    def on_error(self, error: Exception, **kwargs) -> bool:
        logger.error(f"Request failed with error: {error}")
        return False  # Не повторять запрос, просто логировать
