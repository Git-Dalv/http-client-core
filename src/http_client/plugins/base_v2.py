"""Plugin base class v2 with RequestContext support."""

from abc import ABC, abstractmethod
from typing import Optional
import requests

from ..core.context import RequestContext


class PluginV2(ABC):
    """Base class for plugins using RequestContext API (v2).

    This is the recommended plugin API starting from v2.0.

    Key differences from v1:
    - before_request receives full context and can return Response
    - after_response has access to request parameters via context
    - Explicit request_id for tracing

    Example:
        class MyPlugin(PluginV2):
            def before_request(self, ctx: RequestContext) -> Optional[requests.Response]:
                # Access all request info
                print(f"Request {ctx.request_id}: {ctx.method} {ctx.url}")

                # Can return Response to short-circuit
                if ctx.url in self.blocked_urls:
                    resp = requests.Response()
                    resp.status_code = 403
                    return resp

                return None  # Continue normally

            def after_response(self, ctx: RequestContext, response: requests.Response):
                # Full context available
                print(f"Response for {ctx.method} {ctx.url}: {response.status_code}")
                return response
    """

    def before_request(self, ctx: RequestContext) -> Optional[requests.Response]:
        """Called before making HTTP request.

        Args:
            ctx: Request context with method, url, kwargs

        Returns:
            - None: Continue with request normally
            - Response: Short-circuit and return this response

        Note:
            Can modify ctx.kwargs in-place to change request parameters.
            Can use ctx.metadata to communicate with other plugins.
        """
        return None

    def after_response(self, ctx: RequestContext, response: requests.Response) -> requests.Response:
        """Called after receiving HTTP response.

        Args:
            ctx: Request context (same object from before_request)
            response: HTTP response

        Returns:
            Modified or original response

        Note:
            Has full access to request parameters via ctx.
            Can use ctx.metadata to access data from before_request.
        """
        return response

    def on_error(self, ctx: RequestContext, error: Exception) -> bool:
        """Called when request fails.

        Args:
            ctx: Request context
            error: Exception that occurred

        Returns:
            True if request should be retried, False otherwise
        """
        return False
