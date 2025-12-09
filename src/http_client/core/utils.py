"""
Utility functions for HTTP client.

Includes:
- URL sanitization for safe logging
- Security helpers
"""

from typing import Set, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


# Default sensitive parameter names that should be masked in logs
DEFAULT_SENSITIVE_PARAMS = {
    'api_key',
    'apikey',
    'api-key',
    'token',
    'access_token',
    'accesstoken',
    'refresh_token',
    'key',
    'secret',
    'password',
    'passwd',
    'pwd',
    'auth',
    'authorization',
    'credentials',
    'client_secret',
    'private_key',
    'session',
    'session_id',
    'sessionid',
}


def sanitize_url(
    url: str,
    extra_params: Optional[Set[str]] = None,
    mask: str = 'REDACTED'
) -> str:
    """
    Mask sensitive query parameters in URL for safe logging.

    This function protects against credential leakage in logs by replacing
    sensitive parameter values with a mask string.

    Args:
        url: The URL to sanitize
        extra_params: Additional parameter names to mask (case-insensitive)
        mask: The string to use for masking (default: 'REDACTED')

    Returns:
        Sanitized URL with sensitive parameters masked

    Examples:
        >>> sanitize_url('https://api.example.com/data?api_key=secret123')
        'https://api.example.com/data?api_key=REDACTED'

        >>> sanitize_url('https://api.example.com/data?user=john&token=abc123')
        'https://api.example.com/data?user=john&token=REDACTED'

        >>> sanitize_url(
        ...     'https://api.example.com/data?custom=secret',
        ...     extra_params={'custom'}
        ... )
        'https://api.example.com/data?custom=REDACTED'

    Security:
        - Case-insensitive matching for parameter names
        - Preserves URL structure
        - Handles multiple values for same parameter
        - Safe for URLs without query strings
    """
    if not url:
        return url

    try:
        # Combine default and extra sensitive params (lowercase for comparison)
        sensitive_params = DEFAULT_SENSITIVE_PARAMS | (
            {p.lower() for p in extra_params} if extra_params else set()
        )

        parsed = urlparse(url)

        # If no query string, return as-is
        if not parsed.query:
            return url

        # Parse query parameters
        params = parse_qs(parsed.query, keep_blank_values=True)

        # Mask sensitive parameters
        sanitized_params = {}
        for param_name, param_values in params.items():
            if param_name.lower() in sensitive_params:
                # Mask all values for this parameter
                sanitized_params[param_name] = [mask] * len(param_values)
            else:
                sanitized_params[param_name] = param_values

        # Reconstruct query string
        new_query = urlencode(sanitized_params, doseq=True)

        # Reconstruct URL
        return urlunparse(parsed._replace(query=new_query))

    except Exception:
        # If sanitization fails for any reason, return a safe fallback
        # Don't risk exposing the original URL
        return '<URL sanitization failed>'


def sanitize_headers(headers: dict, mask: str = 'REDACTED') -> dict:
    """
    Mask sensitive headers for safe logging.

    Args:
        headers: Dictionary of headers
        mask: The string to use for masking

    Returns:
        Sanitized headers dictionary

    Examples:
        >>> sanitize_headers({'Authorization': 'Bearer token123'})
        {'Authorization': 'REDACTED'}
    """
    if not headers:
        return headers

    sensitive_header_names = {
        'authorization',
        'api-key',
        'x-api-key',
        'x-auth-token',
        'cookie',
        'set-cookie',
        'proxy-authorization',
        'x-csrf-token',
        'x-session-token',
    }

    sanitized = {}
    for key, value in headers.items():
        if key.lower() in sensitive_header_names:
            sanitized[key] = mask
        else:
            sanitized[key] = value

    return sanitized
