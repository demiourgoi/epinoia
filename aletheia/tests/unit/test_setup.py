import json
import subprocess
import sys
from pathlib import Path

import pytest

from aletheia_mcp.setup import HOOK_NAME, install_hook


def test_install_creates_files(tmp_path: Path) -> None:
    hooks_toml = install_hook(tmp_path)
    assert hooks_toml == tmp_path / ".vibe" / "hooks.toml"
    content = hooks_toml.read_text()
    assert f'name = "{HOOK_NAME}"' in content
    assert 'type = "post_tool"' in content
    script = tmp_path / ".vibe" / "hooks" / "aletheia_baseline.py"
    assert script.exists()


def test_install_is_idempotent_and_merge_safe(tmp_path: Path) -> None:
    hooks_toml = tmp_path / ".vibe" / "hooks.toml"
    hooks_toml.parent.mkdir(parents=True)
    hooks_toml.write_text('[[hooks]]\nname = "other"\ntype = "pre_tool"\ncommand = "true"\n')
    install_hook(tmp_path)
    first = hooks_toml.read_text()
    assert first.startswith('[[hooks]]\nname = "other"')
    assert first.count(HOOK_NAME) == 1
    install_hook(tmp_path)
    assert hooks_toml.read_text() == first


def test_hook_script_reminds_on_edit(tmp_path: Path) -> None:
    install_hook(tmp_path)
    script = tmp_path / ".vibe" / "hooks" / "aletheia_baseline.py"
    payload = {"tool_status": "success", "tool_input": {"file_path": "src/main.py"}}
    result = subprocess.run(
        [sys.executable, str(script)], input=json.dumps(payload), capture_output=True, text=True, check=True
    )
    output = json.loads(result.stdout)
    assert "src/main.py" in output["hook_specific_output"]["additional_context"]
    assert "record_baseline" in output["hook_specific_output"]["additional_context"]


def test_hook_script_silent_on_unrelated_payload(tmp_path: Path) -> None:
    install_hook(tmp_path)
    script = tmp_path / ".vibe" / "hooks" / "aletheia_baseline.py"
    for payload in (
        {"tool_status": "failure", "tool_input": {"file_path": "x"}},
        {"tool_status": "success", "tool_input": {"command": "ls"}},
        {"tool_status": "success", "tool_input": {}},
    ):
        result = subprocess.run(
            [sys.executable, str(script)], input=json.dumps(payload), capture_output=True, text=True, check=True
        )
        assert result.stdout == ""


def test_git_root_resolves_repository(tmp_path: Path) -> None:
    import subprocess

    base = tmp_path / "repo"
    base.mkdir()
    subprocess.run(["git", "-C", str(base), "init", "-q"], check=True)  # noqa: S607
    nested = base / "deep" / "nested"
    nested.mkdir(parents=True)
    from aletheia_mcp.setup import git_root

    assert git_root(nested) == base.resolve()


def test_git_root_none_when_git_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    import aletheia_mcp.setup as setup_module

    def boom(*args: object, **kwargs: object) -> object:
        raise OSError

    monkeypatch.setattr(setup_module.subprocess, "run", boom)
    assert setup_module.git_root(Path(".")) is None


def test_setup_installs_at_git_root(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    import subprocess

    from aletheia_mcp.main import setup

    base = tmp_path / "repo"
    base.mkdir()
    subprocess.run(["git", "-C", str(base), "init", "-q"], check=True)  # noqa: S607
    nested = base / "pkg" / "module"
    nested.mkdir(parents=True)

    setup(directory=nested)

    assert (base / ".vibe" / "hooks.toml").exists()
    assert (base / ".vibe" / "hooks" / "aletheia_baseline.py").exists()
    assert not (nested / ".vibe").exists()
    assert "git root" in capsys.readouterr().out
