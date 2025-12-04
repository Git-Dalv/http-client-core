"""
Secret masking for secure logging.

Prevents secrets from appearing in logs.
"""

import re
from typing import Any, Dict


def mask_secret(value: str, visible_chars: int = 4) -> str:
    """
    Mask secret value for logging.

    Shows first and last few characters, masks the middle.

    Args:
        value: Secret to mask
        visible_chars: Number of visible characters at start/end

    Returns:
        Masked string

    Example:
        >>> mask_secret("my-secret-api-key-12345", visible_chars=4)
        'my-s***2345'
        >>> mask_secret("short", visible_chars=2)
        '***'
    """
    if not value:
        return ""

    if len(value) <= (visible_chars * 2):
        return "***"

    start = value[:visible_chars]
    end = value[-visible_chars:]
    return f"{start}***{end}"


def mask_dict_secrets(data: Dict[str, Any], secret_keys: set = None) -> Dict[str, Any]:
    """
    Mask secrets in dictionary.

    Args:
        data: Dictionary potentially containing secrets
        secret_keys: Set of keys to mask (default: common secret names)

    Returns:
        Dictionary with masked secrets

    Example:
        >>> data = {"api_key": "secret123", "username": "john"}
        >>> mask_dict_secrets(data)
        {'api_key': 'sec***123', 'username': 'john'}
    """
    if secret_keys is None:
        secret_keys = {
            'api_key', 'api_secret', 'password', 'token', 'secret',
            'auth_token', 'access_token', 'refresh_token', 'private_key',
            'api_password', 'db_password', 'jwt_secret',
        }

    masked = {}
    for key, value in data.items():
        key_lower = key.lower()

        # Check if key contains any secret keyword
        is_secret = any(secret_word in key_lower for secret_word in secret_keys)

        if is_secret and isinstance(value, str):
            masked[key] = mask_secret(value)
        else:
            masked[key] = value

    return masked


def is_secret_key(key: str) -> bool:
    """
    Check if key name suggests it's a secret.

    Args:
        key: Key name to check

    Returns:
        True if key is likely a secret

    Example:
        >>> is_secret_key("api_key")
        True
        >>> is_secret_key("username")
        False
    """
    secret_patterns = [
        r'.*key.*',
        r'.*secret.*',
        r'.*password.*',
        r'.*token.*',
        r'.*auth.*',
        r'.*private.*',
    ]

    key_lower = key.lower()
    return any(re.match(pattern, key_lower) for pattern in secret_patterns)
