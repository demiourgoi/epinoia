from aletheia_mcp.settings import Settings


def test_defaults() -> None:
    s = Settings()
    assert s.host == "127.0.0.1"
    assert s.port == 8417
    assert s.max_sessions == 100


def test_env_overrides(monkeypatch: object) -> None:
    mp = monkeypatch  # type: ignore[attr-defined]
    mp.setenv("ALETHEIA_PORT", "9001")
    mp.setenv("ALETHEIA_MAX_SESSIONS", "7")
    s = Settings()
    assert s.port == 9001
    assert s.max_sessions == 7


def test_invalid_port_rejected() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(port=0)
