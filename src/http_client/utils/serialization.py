"""
Response serialization utilities for caching plugins.

Provides functions to serialize/deserialize requests.Response objects
for storage in cache systems.
"""

from typing import Dict, Any
from datetime import timedelta
import requests


def serialize_response(response: requests.Response) -> Dict[str, Any]:
    """
    Convert requests.Response to pickleable dictionary.

    Args:
        response: requests.Response object to serialize

    Returns:
        Dictionary with response data that can be pickled/cached

    Note:
        Does not preserve:
        - response.raw (stream)
        - response.connection
        - response.history (for simplicity)

    Example:
        >>> resp = requests.get("https://httpbin.org/get")
        >>> data = serialize_response(resp)
        >>> # data can now be pickled or stored in cache
    """
    return {
        'status_code': response.status_code,
        'headers': dict(response.headers),
        'content': response.content,
        'url': response.url,
        'encoding': response.encoding,
        'reason': response.reason,
        'elapsed': response.elapsed.total_seconds() if response.elapsed else 0,
    }


def deserialize_response(data: Dict[str, Any]) -> requests.Response:
    """
    Reconstruct requests.Response from serialized dictionary.

    Args:
        data: Dictionary from serialize_response()

    Returns:
        requests.Response object with restored data

    Note:
        This is a reconstructed Response - some methods may not work
        exactly as original (e.g., .json() depends on content-type header)

    Example:
        >>> data = {'status_code': 200, 'content': b'test', ...}
        >>> resp = deserialize_response(data)
        >>> assert resp.status_code == 200
        >>> assert resp.content == b'test'
    """
    response = requests.Response()
    response.status_code = data['status_code']
    response._content = data['content']
    response.headers = requests.structures.CaseInsensitiveDict(data['headers'])
    response.url = data['url']
    response.encoding = data.get('encoding')
    response.reason = data.get('reason', '')

    # Restore elapsed time
    elapsed_seconds = data.get('elapsed', 0)
    response.elapsed = timedelta(seconds=elapsed_seconds)

    return response
