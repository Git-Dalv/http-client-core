"""
Tests for secret masking functionality.
"""

import pytest
from src.http_client.core.env_config.secrets import (
    mask_secret,
    mask_dict_secrets,
    is_secret_key,
)


class TestMaskSecret:
    """Test mask_secret function."""

    def test_mask_long_secret(self):
        """Test masking long secret."""
        secret = "my-super-secret-api-key-12345"
        masked = mask_secret(secret, visible_chars=4)
        assert masked == "my-s***2345"

    def test_mask_short_secret(self):
        """Test masking short secret."""
        secret = "short"
        masked = mask_secret(secret, visible_chars=4)
        assert masked == "***"

    def test_mask_empty_string(self):
        """Test masking empty string."""
        assert mask_secret("") == ""

    def test_mask_different_visible_chars(self):
        """Test different visible_chars values."""
        secret = "test-secret-key-123"
        assert mask_secret(secret, visible_chars=2) == "te***23"
        assert mask_secret(secret, visible_chars=6) == "test-s***ey-123"

    def test_mask_exactly_double_visible(self):
        """Test secret exactly double the visible chars."""
        secret = "12345678"  # 8 chars with visible_chars=4
        masked = mask_secret(secret, visible_chars=4)
        assert masked == "***"


class TestMaskDictSecrets:
    """Test mask_dict_secrets function."""

    def test_mask_api_key(self):
        """Test masking API key in dict."""
        data = {"api_key": "secret-key-123456"}
        masked = mask_dict_secrets(data)
        assert masked["api_key"] == "secr***3456"

    def test_mask_password(self):
        """Test masking password in dict."""
        data = {"password": "MyPassword123"}
        masked = mask_dict_secrets(data)
        assert masked["password"] == "MyPa***d123"

    def test_dont_mask_normal_fields(self):
        """Test that normal fields are not masked."""
        data = {"username": "john_doe", "email": "john@example.com"}
        masked = mask_dict_secrets(data)
        assert masked["username"] == "john_doe"
        assert masked["email"] == "john@example.com"

    def test_mask_multiple_secrets(self):
        """Test masking multiple secrets."""
        data = {
            "api_key": "key-123456",
            "password": "pass-123456",
            "username": "john",
        }
        masked = mask_dict_secrets(data)
        assert "***" in masked["api_key"]
        assert "***" in masked["password"]
        assert masked["username"] == "john"

    def test_custom_secret_keys(self):
        """Test with custom secret keys."""
        data = {"custom_field": "secret123"}
        masked = mask_dict_secrets(data, secret_keys={"custom_field"})
        assert "***" in masked["custom_field"]

    def test_case_insensitive_matching(self):
        """Test case-insensitive secret key matching."""
        data = {"API_KEY": "secret123", "Api_Secret": "secret456"}
        masked = mask_dict_secrets(data)
        assert "***" in masked["API_KEY"]
        assert "***" in masked["Api_Secret"]


class TestIsSecretKey:
    """Test is_secret_key function."""

    def test_api_key(self):
        """Test API key detection."""
        assert is_secret_key("api_key") is True
        assert is_secret_key("API_KEY") is True

    def test_password(self):
        """Test password detection."""
        assert is_secret_key("password") is True
        assert is_secret_key("db_password") is True

    def test_token(self):
        """Test token detection."""
        assert is_secret_key("token") is True
        assert is_secret_key("auth_token") is True
        assert is_secret_key("access_token") is True

    def test_secret(self):
        """Test secret detection."""
        assert is_secret_key("secret") is True
        assert is_secret_key("api_secret") is True

    def test_non_secret_keys(self):
        """Test non-secret keys."""
        assert is_secret_key("username") is False
        assert is_secret_key("email") is False
        assert is_secret_key("name") is False
        assert is_secret_key("id") is False
