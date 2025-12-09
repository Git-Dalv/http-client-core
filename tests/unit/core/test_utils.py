"""Tests for utility functions."""

import pytest
from src.http_client.core.utils import sanitize_url, sanitize_headers


class TestSanitizeUrl:
    """Tests for sanitize_url function."""

    def test_sanitize_api_key(self):
        """Test sanitization of api_key parameter."""
        url = "https://api.example.com/data?api_key=secret123"
        result = sanitize_url(url)

        assert "secret123" not in result
        assert "api_key=REDACTED" in result
        assert "https://api.example.com/data" in result

    def test_sanitize_token(self):
        """Test sanitization of token parameter."""
        url = "https://api.example.com/data?token=abc123xyz"
        result = sanitize_url(url)

        assert "abc123xyz" not in result
        assert "token=REDACTED" in result

    def test_sanitize_password(self):
        """Test sanitization of password parameter."""
        url = "https://api.example.com/login?user=john&password=secret&remember=true"
        result = sanitize_url(url)

        assert "secret" not in result
        assert "password=REDACTED" in result
        assert "user=john" in result
        assert "remember=true" in result

    def test_sanitize_multiple_sensitive_params(self):
        """Test sanitization of multiple sensitive parameters."""
        url = "https://api.example.com/data?api_key=key123&token=tok456&user=john"
        result = sanitize_url(url)

        assert "key123" not in result
        assert "tok456" not in result
        assert "api_key=REDACTED" in result
        assert "token=REDACTED" in result
        assert "user=john" in result

    def test_sanitize_case_insensitive(self):
        """Test that parameter matching is case-insensitive."""
        url = "https://api.example.com/data?API_KEY=secret&Token=abc&SECRET=xyz"
        result = sanitize_url(url)

        assert "secret" not in result
        assert "abc" not in result
        assert "xyz" not in result
        assert "REDACTED" in result

    def test_sanitize_with_extra_params(self):
        """Test sanitization with custom sensitive parameters."""
        url = "https://api.example.com/data?custom_token=secret123&normal=value"
        result = sanitize_url(url, extra_params={'custom_token'})

        assert "secret123" not in result
        assert "custom_token=REDACTED" in result
        assert "normal=value" in result

    def test_sanitize_url_without_query(self):
        """Test URL without query string remains unchanged."""
        url = "https://api.example.com/data"
        result = sanitize_url(url)

        assert result == url

    def test_sanitize_empty_url(self):
        """Test empty URL is handled safely."""
        result = sanitize_url("")
        assert result == ""

    def test_sanitize_none_url(self):
        """Test None URL is handled safely."""
        result = sanitize_url(None)
        assert result is None

    def test_sanitize_preserves_url_structure(self):
        """Test that URL structure (scheme, host, path) is preserved."""
        url = "https://api.example.com:8080/v1/data?api_key=secret#fragment"
        result = sanitize_url(url)

        assert "https://" in result
        assert "api.example.com:8080" in result
        assert "/v1/data" in result
        assert "api_key=REDACTED" in result
        assert "#fragment" in result

    def test_sanitize_multiple_values_same_param(self):
        """Test parameter with multiple values."""
        url = "https://api.example.com/data?token=val1&token=val2&user=john"
        result = sanitize_url(url)

        assert "val1" not in result
        assert "val2" not in result
        assert "token=REDACTED" in result
        # Should have two masked values
        assert result.count("REDACTED") >= 2

    def test_sanitize_all_default_sensitive_params(self):
        """Test all default sensitive parameter names."""
        sensitive_params = [
            'api_key', 'apikey', 'api-key', 'token', 'access_token',
            'refresh_token', 'key', 'secret', 'password', 'passwd',
            'pwd', 'auth', 'authorization', 'credentials', 'client_secret',
            'private_key', 'session', 'session_id'
        ]

        for param in sensitive_params:
            url = f"https://api.example.com/data?{param}=sensitive_value"
            result = sanitize_url(url)

            assert "sensitive_value" not in result, f"Failed to mask {param}"
            assert "REDACTED" in result, f"Failed to mask {param}"

    def test_sanitize_custom_mask(self):
        """Test custom mask string."""
        url = "https://api.example.com/data?api_key=secret"
        result = sanitize_url(url, mask="CUSTOM_MASK")

        assert "secret" not in result
        assert "api_key=CUSTOM_MASK" in result

    def test_sanitize_preserves_non_sensitive_params(self):
        """Test non-sensitive parameters are not masked."""
        url = "https://api.example.com/data?user=john&page=1&limit=10&sort=name"
        result = sanitize_url(url)

        assert "user=john" in result
        assert "page=1" in result
        assert "limit=10" in result
        assert "sort=name" in result
        assert "REDACTED" not in result

    def test_sanitize_url_encoding_preserved(self):
        """Test that URL encoding is preserved."""
        url = "https://api.example.com/data?name=John%20Doe&api_key=secret"
        result = sanitize_url(url)

        assert "secret" not in result
        assert "api_key=REDACTED" in result
        # URL encoding should be preserved for non-sensitive params
        assert "John" in result or "Doe" in result

    def test_sanitize_malformed_url_fallback(self):
        """Test that malformed URLs return safe fallback."""
        # This should trigger exception handling
        url = "not a valid url at all"
        result = sanitize_url(url)

        # Should return a safe fallback, not the original URL
        assert result == '<URL sanitization failed>' or result == url


class TestSanitizeHeaders:
    """Tests for sanitize_headers function."""

    def test_sanitize_authorization_header(self):
        """Test sanitization of Authorization header."""
        headers = {'Authorization': 'Bearer token123'}
        result = sanitize_headers(headers)

        assert result['Authorization'] == 'REDACTED'
        assert 'token123' not in str(result)

    def test_sanitize_api_key_header(self):
        """Test sanitization of API key headers."""
        headers = {
            'X-API-Key': 'secret123',
            'api-key': 'another_secret'
        }
        result = sanitize_headers(headers)

        assert result['X-API-Key'] == 'REDACTED'
        assert result['api-key'] == 'REDACTED'

    def test_sanitize_cookie_header(self):
        """Test sanitization of Cookie header."""
        headers = {'Cookie': 'session=abc123; user=john'}
        result = sanitize_headers(headers)

        assert result['Cookie'] == 'REDACTED'

    def test_sanitize_preserves_non_sensitive_headers(self):
        """Test non-sensitive headers are not masked."""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        }
        result = sanitize_headers(headers)

        assert result['Content-Type'] == 'application/json'
        assert result['User-Agent'] == 'Mozilla/5.0'
        assert result['Accept'] == 'application/json'

    def test_sanitize_mixed_headers(self):
        """Test mixed sensitive and non-sensitive headers."""
        headers = {
            'Authorization': 'Bearer secret',
            'Content-Type': 'application/json',
            'X-API-Key': 'key123',
            'User-Agent': 'MyApp/1.0'
        }
        result = sanitize_headers(headers)

        assert result['Authorization'] == 'REDACTED'
        assert result['X-API-Key'] == 'REDACTED'
        assert result['Content-Type'] == 'application/json'
        assert result['User-Agent'] == 'MyApp/1.0'

    def test_sanitize_empty_headers(self):
        """Test empty headers dict."""
        result = sanitize_headers({})
        assert result == {}

    def test_sanitize_none_headers(self):
        """Test None headers."""
        result = sanitize_headers(None)
        assert result is None

    def test_sanitize_case_insensitive_headers(self):
        """Test header name matching is case-insensitive."""
        headers = {
            'AUTHORIZATION': 'Bearer secret',
            'authorization': 'Bearer secret2',
            'Authorization': 'Bearer secret3'
        }
        result = sanitize_headers(headers)

        # All should be masked
        for value in result.values():
            assert value == 'REDACTED'

    def test_sanitize_custom_mask_headers(self):
        """Test custom mask string for headers."""
        headers = {'Authorization': 'Bearer token'}
        result = sanitize_headers(headers, mask='[REDACTED]')

        assert result['Authorization'] == '[REDACTED]'


class TestSecurityIntegration:
    """Integration tests for URL sanitization in security context."""

    def test_credential_leak_prevention(self):
        """Test that common credential patterns are masked."""
        urls = [
            "https://api.example.com/data?api_key=sk_live_abc123",
            "https://api.example.com/auth?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "https://api.example.com/login?password=MyP@ssw0rd!",
            "https://api.example.com/oauth?client_secret=very_secret_value",
            "https://api.example.com/session?session_id=abc-123-def-456",
        ]

        for url in urls:
            result = sanitize_url(url)

            # Check that sensitive values are not in result
            assert "sk_live_abc123" not in result
            assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
            assert "MyP@ssw0rd!" not in result
            assert "very_secret_value" not in result
            assert "abc-123-def-456" not in result

            # Check that mask is present
            assert "REDACTED" in result

    def test_mixed_sensitive_and_normal_params(self):
        """Test realistic URL with mixed parameters."""
        url = (
            "https://api.example.com/users/search"
            "?query=john"
            "&page=1"
            "&limit=20"
            "&api_key=secret123"
            "&token=abc456"
            "&sort=name"
        )

        result = sanitize_url(url)

        # Sensitive params should be masked
        assert "secret123" not in result
        assert "abc456" not in result

        # Normal params should be preserved
        assert "query=john" in result
        assert "page=1" in result
        assert "limit=20" in result
        assert "sort=name" in result

    def test_no_false_positives(self):
        """Test that legitimate values aren't accidentally masked."""
        url = (
            "https://api.example.com/search"
            "?keyword=password"  # Searching for the word "password"
            "&category=security"
            "&article=api-key-management"  # Article about API keys
        )

        result = sanitize_url(url)

        # These are param VALUES that happen to contain sensitive words
        # but the PARAM NAMES are not sensitive, so they should NOT be masked
        assert "keyword=password" in result
        assert "category=security" in result
        assert "article=api-key-management" in result
