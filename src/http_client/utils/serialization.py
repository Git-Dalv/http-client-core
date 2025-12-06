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

        Now preserves (v2):
        - cookies
        - history (redirect chain)
        - original request metadata

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
        # V2 additions: cookies, history, request
        'cookies': dict(response.cookies) if response.cookies else {},
        'history': [
            {
                'status_code': r.status_code,
                'url': r.url,
                'headers': dict(r.headers),
            }
            for r in response.history
        ] if response.history else [],
        'request': {
            'method': response.request.method if response.request else None,
            'url': response.request.url if response.request else None,
            'headers': dict(response.request.headers) if response.request and response.request.headers else {},
        } if response.request else None,
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

        V2 additions (backward compatible):
        - Restores cookies if present
        - Restores history (redirect chain) if present
        - Restores request metadata if present

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

    # V2: Restore cookies (backward compatible - check if key exists)
    if 'cookies' in data and data['cookies']:
        for name, value in data['cookies'].items():
            response.cookies.set(name, value)

    # V2: Restore history (backward compatible)
    if 'history' in data and data['history']:
        response.history = []
        for hist_data in data['history']:
            hist_resp = requests.Response()
            hist_resp.status_code = hist_data['status_code']
            hist_resp.url = hist_data['url']
            hist_resp.headers = requests.structures.CaseInsensitiveDict(hist_data['headers'])
            response.history.append(hist_resp)

    # V2: Restore request metadata (backward compatible)
    if 'request' in data and data['request']:
        response.request = requests.PreparedRequest()
        response.request.method = data['request'].get('method')
        response.request.url = data['request'].get('url')
        response.request.headers = data['request'].get('headers', {})

    return response
