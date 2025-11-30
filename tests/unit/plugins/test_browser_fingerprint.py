"""
Comprehensive tests for BrowserFingerprintPlugin - complete coverage.
"""

from unittest.mock import Mock

import pytest
import requests

from src.http_client.plugins.browser_fingerprint import (
    BROWSER_PROFILES,
    BrowserFingerprintPlugin,
    BrowserProfile,
)


class TestBrowserProfile:
    """Test BrowserProfile class."""

    def test_profile_initialization(self):
        """Test profile initialization with minimal parameters."""
        profile = BrowserProfile(name="TestBrowser", user_agent="Mozilla/5.0 (Test) Browser/1.0")

        assert profile.name == "TestBrowser"
        assert profile.user_agent == "Mozilla/5.0 (Test) Browser/1.0"
        assert profile.accept_language == "en-US,en;q=0.9"
        assert profile.accept_encoding == "gzip, deflate, br"

    def test_profile_with_all_parameters(self):
        """Test profile initialization with all parameters."""
        profile = BrowserProfile(
            name="Chrome",
            user_agent="Mozilla/5.0 Chrome/120.0",
            sec_ch_ua='"Chrome";v="120"',
            sec_ch_ua_mobile="?0",
            sec_ch_ua_platform='"Windows"',
            accept="text/html",
            accept_language="ru-RU,ru;q=0.9",
            accept_encoding="gzip",
            upgrade_insecure_requests="1",
            sec_fetch_dest="document",
            sec_fetch_mode="navigate",
            sec_fetch_site="none",
            sec_fetch_user="?1",
        )

        assert profile.name == "Chrome"
        assert profile.sec_ch_ua == '"Chrome";v="120"'
        assert profile.sec_ch_ua_platform == '"Windows"'
        assert profile.accept == "text/html"
        assert profile.accept_language == "ru-RU,ru;q=0.9"

    def test_generate_headers_basic(self):
        """Test basic header generation."""
        profile = BrowserProfile(name="TestBrowser", user_agent="Mozilla/5.0 (Test) Browser/1.0")

        headers = profile.generate_headers()

        assert "User-Agent" in headers
        assert headers["User-Agent"] == "Mozilla/5.0 (Test) Browser/1.0"
        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert "Accept-Encoding" in headers

    def test_generate_headers_with_client_hints(self):
        """Test header generation with Client Hints."""
        profile = BrowserProfile(
            name="Chrome",
            user_agent="Mozilla/5.0 Chrome/120.0",
            sec_ch_ua='"Chrome";v="120"',
            sec_ch_ua_platform='"Windows"',
        )

        headers = profile.generate_headers()

        assert "Sec-CH-UA" in headers
        assert headers["Sec-CH-UA"] == '"Chrome";v="120"'
        assert "Sec-CH-UA-Mobile" in headers
        assert "Sec-CH-UA-Platform" in headers
        assert headers["Sec-CH-UA-Platform"] == '"Windows"'

    def test_generate_headers_without_client_hints(self):
        """Test header generation without Client Hints (Firefox/Safari)."""
        profile = BrowserProfile(
            name="Firefox",
            user_agent="Mozilla/5.0 Firefox/121.0",
            sec_ch_ua=None,
            sec_ch_ua_platform=None,
        )

        headers = profile.generate_headers()

        assert "Sec-CH-UA" not in headers
        assert "Sec-CH-UA-Platform" not in headers
        assert "User-Agent" in headers

    def test_generate_headers_with_fetch_metadata(self):
        """Test header generation with Fetch Metadata."""
        profile = BrowserProfile(
            name="Chrome",
            user_agent="Mozilla/5.0 Chrome/120.0",
            sec_fetch_dest="document",
            sec_fetch_mode="navigate",
            sec_fetch_site="none",
            sec_fetch_user="?1",
        )

        headers = profile.generate_headers()

        assert "Sec-Fetch-Dest" in headers
        assert headers["Sec-Fetch-Dest"] == "document"
        assert "Sec-Fetch-Mode" in headers
        assert headers["Sec-Fetch-Mode"] == "navigate"
        assert "Sec-Fetch-Site" in headers
        assert "Sec-Fetch-User" in headers


class TestBrowserFingerprintPluginInit:
    """Test BrowserFingerprintPlugin initialization."""

    def test_init_with_chrome(self):
        """Test initialization with Chrome browser."""
        plugin = BrowserFingerprintPlugin(browser="chrome")

        assert plugin.browser == "chrome"
        assert plugin.random_profile is False
        assert plugin._current_profile is not None
        assert plugin._current_profile.name == "Chrome"

    def test_init_with_firefox(self):
        """Test initialization with Firefox browser."""
        plugin = BrowserFingerprintPlugin(browser="firefox")

        assert plugin.browser == "firefox"
        assert plugin._current_profile.name == "Firefox"

    def test_init_with_safari(self):
        """Test initialization with Safari browser."""
        plugin = BrowserFingerprintPlugin(browser="safari")

        assert plugin.browser == "safari"
        assert plugin._current_profile.name == "Safari"

    def test_init_with_edge(self):
        """Test initialization with Edge browser."""
        plugin = BrowserFingerprintPlugin(browser="edge")

        assert plugin.browser == "edge"
        assert plugin._current_profile.name == "Edge"

    def test_init_with_chrome_mobile(self):
        """Test initialization with Chrome Mobile browser."""
        plugin = BrowserFingerprintPlugin(browser="chrome_mobile")

        assert plugin.browser == "chrome_mobile"
        assert plugin._current_profile.name == "Chrome Mobile"

    def test_init_with_unknown_browser(self):
        """Test initialization with unknown browser raises ValueError."""
        with pytest.raises(ValueError, match="Unknown browser"):
            BrowserFingerprintPlugin(browser="unknown")

    def test_init_with_random_profile(self):
        """Test initialization with random profile mode."""
        plugin = BrowserFingerprintPlugin(random_profile=True)

        assert plugin.random_profile is True
        assert plugin._current_profile is None

    def test_init_with_random_profile_and_browser(self):
        """Test that random_profile overrides browser selection."""
        plugin = BrowserFingerprintPlugin(browser="chrome", random_profile=True)

        assert plugin.random_profile is True
        assert plugin._current_profile is None


class TestBrowserFingerprintPluginMethods:
    """Test BrowserFingerprintPlugin methods."""

    def test_get_current_profile_fixed(self):
        """Test get_current_profile with fixed browser."""
        plugin = BrowserFingerprintPlugin(browser="chrome")

        profile = plugin.get_current_profile()

        assert profile is not None
        assert profile.name == "Chrome"
        # Should return same profile each time
        assert plugin.get_current_profile() is profile

    def test_get_current_profile_random(self):
        """Test get_current_profile with random mode."""
        plugin = BrowserFingerprintPlugin(random_profile=True)

        # Call multiple times, should get valid profiles
        for _ in range(10):
            profile = plugin.get_current_profile()
            assert profile is not None
            assert profile.name in ["Chrome", "Firefox", "Safari", "Edge", "Chrome Mobile"]

    def test_generate_headers(self):
        """Test generate_headers method."""
        plugin = BrowserFingerprintPlugin(browser="chrome")

        headers = plugin.generate_headers()

        assert isinstance(headers, dict)
        assert "User-Agent" in headers
        assert "Chrome" in headers["User-Agent"]

    def test_set_browser_to_firefox(self):
        """Test changing browser to Firefox."""
        plugin = BrowserFingerprintPlugin(browser="chrome")

        plugin.set_browser("firefox")

        assert plugin.browser == "firefox"
        assert plugin.random_profile is False
        assert plugin._current_profile.name == "Firefox"

    def test_set_browser_to_unknown(self):
        """Test setting unknown browser raises ValueError."""
        plugin = BrowserFingerprintPlugin(browser="chrome")

        with pytest.raises(ValueError, match="Unknown browser"):
            plugin.set_browser("unknown")

    def test_enable_random_profile(self):
        """Test enabling random profile mode."""
        plugin = BrowserFingerprintPlugin(browser="chrome")

        plugin.enable_random_profile()

        assert plugin.random_profile is True
        assert plugin._current_profile is None

    def test_disable_random_profile(self):
        """Test disabling random profile mode."""
        plugin = BrowserFingerprintPlugin(random_profile=True)
        plugin.browser = "firefox"  # Set a browser

        plugin.disable_random_profile()

        assert plugin.random_profile is False
        assert plugin._current_profile is not None
        assert plugin._current_profile.name == "Firefox"

    def test_get_available_browsers(self):
        """Test getting list of available browsers."""
        browsers = BrowserFingerprintPlugin.get_available_browsers()

        assert isinstance(browsers, list)
        assert "chrome" in browsers
        assert "firefox" in browsers
        assert "safari" in browsers
        assert "edge" in browsers
        assert "chrome_mobile" in browsers


class TestBrowserFingerprintPluginHooks:
    """Test plugin hooks (before_request, after_response, on_error)."""

    def test_before_request_adds_headers(self):
        """Test that before_request adds browser headers."""
        plugin = BrowserFingerprintPlugin(browser="chrome")

        kwargs = {}
        result = plugin.before_request("GET", "https://api.example.com", **kwargs)

        assert "headers" in result
        assert "User-Agent" in result["headers"]
        assert "Chrome" in result["headers"]["User-Agent"]
        assert "Accept" in result["headers"]

    def test_before_request_preserves_existing_headers(self):
        """Test that before_request preserves user's custom headers."""
        plugin = BrowserFingerprintPlugin(browser="chrome")

        kwargs = {"headers": {"X-Custom": "CustomValue", "User-Agent": "MyCustomUA"}}
        result = plugin.before_request("GET", "https://api.example.com", **kwargs)

        # Custom header should be preserved
        assert result["headers"]["X-Custom"] == "CustomValue"
        # User's User-Agent should NOT be overwritten
        assert result["headers"]["User-Agent"] == "MyCustomUA"

    def test_before_request_adds_only_missing_headers(self):
        """Test that before_request only adds missing headers."""
        plugin = BrowserFingerprintPlugin(browser="chrome")

        kwargs = {"headers": {"Accept": "application/json"}}
        result = plugin.before_request("GET", "https://api.example.com", **kwargs)

        # User's Accept should be preserved
        assert result["headers"]["Accept"] == "application/json"
        # But User-Agent should be added
        assert "User-Agent" in result["headers"]

    def test_before_request_chrome_headers(self):
        """Test Chrome-specific headers in before_request."""
        plugin = BrowserFingerprintPlugin(browser="chrome")

        result = plugin.before_request("GET", "https://api.example.com")

        # Chrome should have Client Hints
        assert "Sec-CH-UA" in result["headers"]
        assert "Chromium" in result["headers"]["Sec-CH-UA"]

    def test_before_request_firefox_headers(self):
        """Test Firefox-specific headers in before_request."""
        plugin = BrowserFingerprintPlugin(browser="firefox")

        result = plugin.before_request("GET", "https://api.example.com")

        # Firefox should NOT have Client Hints
        assert "Sec-CH-UA" not in result["headers"]
        assert "Firefox" in result["headers"]["User-Agent"]

    def test_after_response(self):
        """Test after_response hook."""
        plugin = BrowserFingerprintPlugin(browser="chrome")
        response = Mock(spec=requests.Response)
        response.status_code = 200

        result = plugin.after_response(response)

        # Should return response unchanged
        assert result is response

    def test_on_error(self):
        """Test on_error hook."""
        plugin = BrowserFingerprintPlugin(browser="chrome")
        error = Exception("Test error")

        result = plugin.on_error(error)

        # Should return False (don't retry)
        assert result is False


class TestBrowserFingerprintPluginProfiles:
    """Test predefined browser profiles."""

    def test_chrome_profile_exists(self):
        """Test Chrome profile is defined."""
        assert "chrome" in BROWSER_PROFILES
        profile = BROWSER_PROFILES["chrome"]
        assert profile.name == "Chrome"
        assert "Chrome" in profile.user_agent
        assert profile.sec_ch_ua is not None

    def test_firefox_profile_exists(self):
        """Test Firefox profile is defined."""
        assert "firefox" in BROWSER_PROFILES
        profile = BROWSER_PROFILES["firefox"]
        assert profile.name == "Firefox"
        assert "Firefox" in profile.user_agent
        assert profile.sec_ch_ua is None  # Firefox doesn't use Client Hints

    def test_safari_profile_exists(self):
        """Test Safari profile is defined."""
        assert "safari" in BROWSER_PROFILES
        profile = BROWSER_PROFILES["safari"]
        assert profile.name == "Safari"
        assert "Safari" in profile.user_agent
        assert profile.sec_ch_ua is None  # Safari doesn't use Client Hints

    def test_edge_profile_exists(self):
        """Test Edge profile is defined."""
        assert "edge" in BROWSER_PROFILES
        profile = BROWSER_PROFILES["edge"]
        assert profile.name == "Edge"
        assert "Edg" in profile.user_agent
        assert profile.sec_ch_ua is not None

    def test_chrome_mobile_profile_exists(self):
        """Test Chrome Mobile profile is defined."""
        assert "chrome_mobile" in BROWSER_PROFILES
        profile = BROWSER_PROFILES["chrome_mobile"]
        assert profile.name == "Chrome Mobile"
        assert "Mobile" in profile.user_agent
        assert profile.sec_ch_ua_mobile == "?1"

    def test_all_profiles_generate_valid_headers(self):
        """Test all profiles generate valid headers."""
        for browser_name, profile in BROWSER_PROFILES.items():
            headers = profile.generate_headers()

            # All profiles should have these basic headers
            assert "User-Agent" in headers
            assert "Accept" in headers
            assert "Accept-Language" in headers
            assert "Accept-Encoding" in headers

            # User-Agent should not be empty
            assert len(headers["User-Agent"]) > 0


class TestBrowserFingerprintPluginIntegration:
    """Test integration scenarios."""

    def test_switch_browser_mid_session(self):
        """Test switching browsers mid-session."""
        plugin = BrowserFingerprintPlugin(browser="chrome")

        # First request with Chrome
        result1 = plugin.before_request("GET", "https://api.example.com")
        assert "Chrome" in result1["headers"]["User-Agent"]

        # Switch to Firefox
        plugin.set_browser("firefox")

        # Second request with Firefox
        result2 = plugin.before_request("GET", "https://api.example.com")
        assert "Firefox" in result2["headers"]["User-Agent"]
        assert "Sec-CH-UA" not in result2["headers"]

    def test_random_profile_generates_different_browsers(self):
        """Test random profile mode generates variety of browsers."""
        plugin = BrowserFingerprintPlugin(random_profile=True)

        # Collect user agents from multiple requests
        user_agents = set()
        for _ in range(20):
            result = plugin.before_request("GET", "https://api.example.com")
            user_agents.add(result["headers"]["User-Agent"])

        # Should have more than one user agent
        assert len(user_agents) > 1

    def test_headers_consistency_within_profile(self):
        """Test that headers are consistent for the same profile."""
        plugin = BrowserFingerprintPlugin(browser="chrome")

        result1 = plugin.before_request("GET", "https://api.example.com")
        result2 = plugin.before_request("GET", "https://api.example.com")

        # Headers should be identical
        assert result1["headers"]["User-Agent"] == result2["headers"]["User-Agent"]
        assert result1["headers"]["Sec-CH-UA"] == result2["headers"]["Sec-CH-UA"]


class TestBrowserFingerprintPluginEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_existing_headers(self):
        """Test with empty existing headers dict."""
        plugin = BrowserFingerprintPlugin(browser="chrome")

        kwargs = {"headers": {}}
        result = plugin.before_request("GET", "https://api.example.com", **kwargs)

        assert "User-Agent" in result["headers"]

    def test_none_values_in_headers(self):
        """Test handling of None values in headers."""
        plugin = BrowserFingerprintPlugin(browser="firefox")

        kwargs = {"headers": {"X-Test": None}}
        result = plugin.before_request("GET", "https://api.example.com", **kwargs)

        # Should not crash, plugin headers should be added
        assert "User-Agent" in result["headers"]

    def test_multiple_before_request_calls(self):
        """Test multiple consecutive before_request calls."""
        plugin = BrowserFingerprintPlugin(browser="safari")

        for _ in range(5):
            result = plugin.before_request("GET", "https://api.example.com")
            assert "User-Agent" in result["headers"]
            assert "Safari" in result["headers"]["User-Agent"]

    def test_plugin_is_instance_of_base_plugin(self):
        """Test that BrowserFingerprintPlugin inherits from Plugin."""
        from src.http_client.plugins.plugin import Plugin

        plugin = BrowserFingerprintPlugin(browser="chrome")
        assert isinstance(plugin, Plugin)
