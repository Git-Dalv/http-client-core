"""Тесты обратной совместимости."""

import pytest
import warnings
import responses
from src.http_client import HTTPClient, __version__


def test_version_available():
    """Version info доступна."""
    assert __version__
    assert isinstance(__version__, str)
    assert len(__version__.split('.')) >= 2  # X.Y format minimum


@responses.activate
def test_old_style_init_still_works():
    """Старый стиль инициализации всё ещё работает."""
    responses.add(responses.GET, "https://api.example.com/test", json={"ok": True})

    # Old style with kwargs
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        client = HTTPClient(
            base_url="https://api.example.com",
            timeout=30,
            max_retries=3
        )

    response = client.get("/test")
    assert response.status_code == 200


def test_deprecated_max_retries_warns():
    """max_retries показывает deprecation warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        client = HTTPClient(
            base_url="https://api.example.com",
            max_retries=5
        )

        # Should have warning
        assert len(w) >= 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "max_retries" in str(w[0].message)
        assert "2.0.0" in str(w[0].message)


def test_deprecated_verify_ssl_warns():
    """verify_ssl показывает deprecation warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        client = HTTPClient(
            base_url="https://api.example.com",
            verify_ssl=False
        )

        assert len(w) >= 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "verify_ssl" in str(w[0].message)


def test_deprecated_pool_connections_warns():
    """pool_connections показывает deprecation warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        client = HTTPClient(
            base_url="https://api.example.com",
            pool_connections=20
        )

        assert len(w) >= 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "pool_connections" in str(w[0].message)


def test_deprecated_max_redirects_warns():
    """max_redirects показывает deprecation warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        client = HTTPClient(
            base_url="https://api.example.com",
            max_redirects=10
        )

        assert len(w) >= 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "max_redirects" in str(w[0].message)


@responses.activate
def test_base_url_property_readable():
    """base_url property работает (обратная совместимость)."""
    responses.add(responses.GET, "https://api.example.com/test", json={})

    client = HTTPClient(base_url="https://api.example.com")

    # Should be readable
    assert client.base_url == "https://api.example.com"


@responses.activate
def test_timeout_property_readable():
    """timeout property работает (обратная совместимость)."""
    responses.add(responses.GET, "https://api.example.com/test", json={})

    client = HTTPClient(base_url="https://api.example.com", timeout=45)

    # Should be readable (returns read timeout for backward compatibility)
    assert client.timeout == 45


def test_immutability_error_message():
    """Immutability error содержит полезное сообщение."""
    client = HTTPClient(base_url="https://api.example.com")

    with pytest.raises(RuntimeError) as exc_info:
        client._config = None

    error_msg = str(exc_info.value)
    assert "immutable" in error_msg.lower()
    assert "new instance" in error_msg.lower()


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
@responses.activate
def test_mixed_old_new_style():
    """Можно мешать старый и новый стиль.

    This test intentionally uses deprecated LoggingPlugin to test backward compatibility.
    """
    responses.add(responses.GET, "https://api.example.com/test", json={})

    from src.http_client import HTTPClientConfig, LoggingPlugin

    # Create config new style
    config = HTTPClientConfig.create(
        base_url="https://api.example.com",
        timeout=30
    )

    # But pass plugins old style (deprecated but should still work)
    plugin = LoggingPlugin()

    client = HTTPClient(config=config, plugins=[plugin])
    response = client.get("/test")

    assert response.status_code == 200


@responses.activate
def test_no_warnings_with_config_object():
    """Использование config объекта не показывает warnings."""
    responses.add(responses.GET, "https://api.example.com/test", json={})

    from src.http_client import HTTPClientConfig

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        config = HTTPClientConfig.create(
            base_url="https://api.example.com",
            timeout=30
        )
        client = HTTPClient(config=config)

        # Should have NO deprecation warnings
        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) == 0

    response = client.get("/test")
    assert response.status_code == 200
