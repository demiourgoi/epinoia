import pytest

from aletheia_mcp.settings import Settings


def test_defaults() -> None:
    settings = Settings()
    assert settings.host == "127.0.0.1"


def test_env_overrides_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALETHEIA_HOST", "localhost")
    assert Settings().host == "localhost"


def test_no_port_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALETHEIA_PORT", "9001")  # deliberately ignored
    monkeypatch.setenv("ALETHEIA_MAX_SESSIONS", "3")  # deliberately ignored
    settings = Settings()
    assert not hasattr(settings, "port")
    assert not hasattr(settings, "max_sessions")
