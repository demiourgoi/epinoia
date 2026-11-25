import pytest

from azathoth.settings import Settings


def test_defaults() -> None:
    settings = Settings()

    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.acp_command == "vibe-acp"
    assert settings.acp_args == []
    assert settings.timeout_secs == 600.0


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZATHOTH_HOST", "::1")
    monkeypatch.setenv("AZATHOTH_PORT", "9000")
    monkeypatch.setenv("AZATHOTH_ACP_COMMAND", "python")
    monkeypatch.setenv("AZATHOTH_ACP_ARGS", '["-m", "fake_agent"]')
    monkeypatch.setenv("AZATHOTH_TIMEOUT_SECS", "30")

    settings = Settings()

    assert settings.host == "::1"
    assert settings.port == 9000
    assert settings.acp_command == "python"
    assert settings.acp_args == ["-m", "fake_agent"]
    assert settings.timeout_secs == 30.0


def test_acp_args_space_separated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZATHOTH_ACP_ARGS", "-m fake_agent --flag")

    settings = Settings()

    assert settings.acp_args == ["-m", "fake_agent", "--flag"]
