import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

import aletheia_mcp.setup as setup_mod
from aletheia_mcp.setup import (
    AGENTS_BEGIN,
    AGENTS_END,
    HOOK_NAME,
    install,
    install_hook,
    merge_agents_md,
    merge_disabled_tools,
    merge_mcp_server,
    server_command,
)


def _servers(text: str) -> list[dict[str, Any]]:
    return tomllib.loads(text).get("mcp_servers", [])


# --- install -----------------------------------------------------------------


def test_install_creates_config_and_agents(tmp_path: Path) -> None:
    messages = install(tmp_path)
    config = (tmp_path / ".vibe" / "config.toml").read_text()
    servers = _servers(config)
    assert [server["name"] for server in servers] == ["aletheia"]
    assert servers[0]["transport"] == "stdio"
    assert servers[0]["command"] == "aletheia"
    assert tomllib.loads(config)["disabled_tools"] == ["edit", "write_file"]
    agents = (tmp_path / ".vibe" / "AGENTS.md").read_text()
    assert "aletheia_edit" in agents
    assert len([line for line in messages if line.startswith("created")]) == 2


def test_install_is_idempotent(tmp_path: Path) -> None:
    install(tmp_path)
    config_path = tmp_path / ".vibe" / "config.toml"
    agents_path = tmp_path / ".vibe" / "AGENTS.md"
    first_config = config_path.read_text()
    first_agents = agents_path.read_text()
    messages = install(tmp_path)
    assert config_path.read_text() == first_config
    assert agents_path.read_text() == first_agents
    assert all(message.startswith("unchanged") for message in messages)


def test_install_preserves_unrelated_config(tmp_path: Path) -> None:
    vibe = tmp_path / ".vibe"
    vibe.mkdir()
    (vibe / "config.toml").write_text(
        'model = "x"  # keep this comment\n\ndisabled_tools = ["bash"]\n\n'
        '[[mcp_servers]]\nname = "other"\ntransport = "http"\nurl = "http://localhost:1"\n'
    )
    install(tmp_path)
    config = (vibe / "config.toml").read_text()
    parsed = tomllib.loads(config)
    assert parsed["model"] == "x"
    assert "# keep this comment" in config
    assert "bash" in parsed["disabled_tools"]
    assert parsed["disabled_tools"][-2:] == ["edit", "write_file"]
    assert [server["name"] for server in parsed["mcp_servers"]] == ["other", "aletheia"]
    assert parsed["mcp_servers"][0]["url"] == "http://localhost:1"


def test_install_preserves_unrelated_agents_md(tmp_path: Path) -> None:
    vibe = tmp_path / ".vibe"
    vibe.mkdir()
    (vibe / "AGENTS.md").write_text("# House rules\n\nBe terse.\n")
    install(tmp_path)
    agents = (vibe / "AGENTS.md").read_text()
    assert agents.startswith("# House rules\n\nBe terse.\n")
    assert agents.count(AGENTS_BEGIN) == 1
    assert agents.count(AGENTS_END) == 1


def test_install_refreshes_managed_section_in_place(tmp_path: Path) -> None:
    vibe = tmp_path / ".vibe"
    vibe.mkdir()
    (vibe / "AGENTS.md").write_text(f"before\n{AGENTS_BEGIN}\nstale text\n{AGENTS_END}\nafter\n")
    install(tmp_path)
    agents = (vibe / "AGENTS.md").read_text()
    assert "stale text" not in agents
    assert agents.startswith("before\n")
    assert agents.endswith("\nafter\n")
    assert agents.count(AGENTS_BEGIN) == 1


def test_install_rejects_invalid_config(tmp_path: Path) -> None:
    vibe = tmp_path / ".vibe"
    vibe.mkdir()
    (vibe / "config.toml").write_text("this is not = [ valid toml\n")
    with pytest.raises(ValueError, match="not valid TOML"):
        install(tmp_path)
    assert (vibe / "config.toml").read_text() == "this is not = [ valid toml\n"


def test_install_uses_uvx_variant_when_launched_by_uvx(tmp_path: Path) -> None:
    install(tmp_path, launched_by_uvx=True)
    server = _servers((tmp_path / ".vibe" / "config.toml").read_text())[0]
    assert server["command"] == "uvx"
    assert server["args"] == ["--from", "epinoia-aletheia", "aletheia"]


def test_install_switches_variant_on_rerun(tmp_path: Path) -> None:
    install(tmp_path)
    install(tmp_path, launched_by_uvx=True)
    server = _servers((tmp_path / ".vibe" / "config.toml").read_text())[0]
    assert server["command"] == "uvx"
    assert (tmp_path / ".vibe" / "config.toml").read_text().count('name = "aletheia"') == 1


def test_server_command_variants() -> None:
    assert server_command(launched_by_uvx=True) == ("uvx", ["--from", "epinoia-aletheia", "aletheia"])
    assert server_command(launched_by_uvx=False) == ("aletheia", [])


# --- config.toml merge --------------------------------------------------------


def test_merge_registers_under_each_server_layout() -> None:
    top = merge_mcp_server("", "aletheia", [])
    assert _servers(top)[0]["name"] == "aletheia"

    named = merge_mcp_server('[mcp_servers]\n\n[mcp_servers.other]\nurl = "http://x"\n', "aletheia", [])
    parsed = tomllib.loads(named)
    assert "other" in parsed["mcp_servers"] and "aletheia" in parsed["mcp_servers"]

    nested = merge_mcp_server(
        '[[model_providers.custom.mcp_servers]]\nname = "other"\ntransport = "stdio"\ncommand = "x"\n',
        "aletheia",
        [],
    )
    names = [server["name"] for server in tomllib.loads(nested)["model_providers"]["custom"]["mcp_servers"]]
    assert names == ["other", "aletheia"]


def test_merge_leaves_a_non_stdio_server_named_aletheia_alone() -> None:
    text = '[[mcp_servers]]\nname = "aletheia"\ntransport = "http"\nurl = "http://remote"\n'
    assert merge_mcp_server(text, "aletheia", []) == text


def test_merge_disabled_tools_keeps_other_entries() -> None:
    text = merge_disabled_tools('disabled_tools = ["bash", "edit"]\n')
    assert tomllib.loads(text)["disabled_tools"] == ["bash", "edit", "write_file"]


def test_merge_disabled_tools_rejects_non_array() -> None:
    with pytest.raises(TypeError, match="not an array"):
        merge_disabled_tools('disabled_tools = "edit"\n')


def test_merge_agents_md_creates_and_appends() -> None:
    assert merge_agents_md("") == merge_agents_md("")
    combined = merge_agents_md("# Rules\n")
    assert combined.startswith("# Rules\n\n")
    assert merge_agents_md(combined) == combined


# --- CLI ----------------------------------------------------------------------


def test_setup_installs_at_git_root(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from aletheia_mcp.main import setup

    base = tmp_path / "repo"
    base.mkdir()
    subprocess.run(["git", "-C", str(base), "init", "-q"], check=True)  # noqa: S607
    nested = base / "pkg" / "module"
    nested.mkdir(parents=True)

    setup(directory=nested)

    assert (base / ".vibe" / "config.toml").exists()
    assert (base / ".vibe" / "AGENTS.md").exists()
    assert not (nested / ".vibe").exists()
    assert "git root" in capsys.readouterr().out


def test_setup_legacy_hook_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from aletheia_mcp.main import setup

    setup(directory=tmp_path, legacy_hook=True)

    assert (tmp_path / ".vibe" / "hooks.toml").exists()
    assert not (tmp_path / ".vibe" / "config.toml").exists()
    assert "prefer the default" in capsys.readouterr().out


def test_launched_by_uvx_detects_archive_interpreter(monkeypatch: pytest.MonkeyPatch) -> None:
    from aletheia_mcp import main

    monkeypatch.setattr(main.sys, "executable", "/home/me/.cache/uv/archive-v0/abc123/bin/python")
    assert main._launched_by_uvx()
    monkeypatch.setattr(main.sys, "executable", "/home/me/project/.venv/bin/python")
    assert not main._launched_by_uvx()


# --- legacy hook (fallback) ---------------------------------------------------


def test_install_hook_creates_files(tmp_path: Path) -> None:
    hooks_toml = install_hook(tmp_path)
    assert hooks_toml == tmp_path / ".vibe" / "hooks.toml"
    content = hooks_toml.read_text()
    assert f'name = "{HOOK_NAME}"' in content
    assert 'type = "post_tool"' in content
    assert (tmp_path / ".vibe" / "hooks" / "aletheia_baseline.py").exists()


def test_install_hook_is_idempotent_and_merge_safe(tmp_path: Path) -> None:
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
    context = json.loads(result.stdout)["hook_specific_output"]["additional_context"]
    assert "src/main.py" in context
    assert "record_baseline" in context


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
    from aletheia_mcp.setup import git_root

    base = tmp_path / "repo"
    base.mkdir()
    subprocess.run(["git", "-C", str(base), "init", "-q"], check=True)  # noqa: S607
    nested = base / "deep" / "nested"
    nested.mkdir(parents=True)

    assert git_root(nested) == base.resolve()


def test_git_root_none_when_git_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: object, **kwargs: object) -> object:
        raise OSError

    monkeypatch.setattr(setup_mod.subprocess, "run", boom)
    assert setup_mod.git_root(Path(".")) is None
