"""Request context for plugin communication."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import uuid


@dataclass
class RequestContext:
    """Context passed through plugin hooks during request lifecycle.

    Attributes:
        request_id: Unique identifier for this request
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        kwargs: Request parameters (params, headers, json, etc.)
        metadata: Shared storage for plugins to communicate

    Example:
        >>> ctx = RequestContext('GET', 'https://api.example.com/users')
        >>> ctx.metadata['cache_key'] = 'abc123'
    """

    method: str
    url: str
    kwargs: Dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def copy(self) -> 'RequestContext':
        """Create a copy of this context."""
        import copy
        return RequestContext(
            method=self.method,
            url=self.url,
            kwargs=copy.deepcopy(self.kwargs),
            request_id=self.request_id,
            metadata=copy.copy(self.metadata)
        )
