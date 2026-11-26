"""Install the recommended Aletheia setup for Mistral Vibe.

`aletheia setup` performs the three manual steps of the README:

1. register the `aletheia` MCP server in `config.toml`;
2. disable Vibe's built-in `edit` and `write_file` tools so the only
   editing path is Aletheia's baseline-aware `edit`;
3. append the editing policy to `AGENTS.md`, the file Vibe loads into the
   agent's context.

The alternative (the "optionally install the reminder hook" fallback that
was the old behaviour of this command, see `install_hook`) is available
with `--legacy-hook`; it works markedly worse.

Every file is edited surgically with tomlkit/Markdown appends, so
installation is idempotent and merge-safe: unrelated content (other MCP
servers, models, comments, prose) is preserved, already-present items are
left untouched, and our own entries are never rewritten.
"""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

import tomlkit
from tomlkit.items import AoT, Array, Table
from tomlkit.toml_document import TOMLDocument

SERVER_NAME = "aletheia"
BUILTIN_TOOLS = ("edit", "write_file")
STDIO = "stdio"

# The manual install (see README) points at the venv's executable; a `uvx`
# run of the same wheel points at `uvx`, which is always current.
LOCAL_COMMAND = "aletheia"
LOCAL_ARGS: list[str] = []
# The PyPI distribution name is `epinoia-aletheia` (`aletheia` and
# `aletheia-mcp` are taken by unrelated projects); the console script it
# installs is still `aletheia`.
UVX_DIST = "epinoia-aletheia"
UVX_COMMAND = "uvx"
UVX_ARGS = ["--from", UVX_DIST, "aletheia"]

AGENTS_BEGIN = "<!-- aletheia:begin (managed by `aletheia setup`) -->"
AGENTS_END = "<!-- aletheia:end -->"
AGENTS_SECTION = f"""\
{AGENTS_BEGIN}
# Aletheia: creating and editing text files

When creating or editing any plain text file:

- You MUST ALWAYS use the tool `aletheia_edit` (Aletheia's MCP `edit`; your host may list it as `mcp_aletheia.edit`)
- If the tool errors, report the failure rather than editing by other means
- You MUST ALWAYS suggest that the user review the changes at the URL the edit tool returns
{AGENTS_END}
"""

HOOK_NAME = "aletheia-baseline"
HOOKS_TOML = """\
[[hooks]]
name = "aletheia-baseline"
type = "post_tool"
match = "re:edit|write_file"
command = "python .vibe/hooks/aletheia_baseline.py"
description = "Remind the agent to record edited files in the Aletheia review baseline."
"""
HOOK_SCRIPT = '''\
"""Aletheia baseline reminder hook (installed by `aletheia setup --legacy-hook`).

Reads the Vibe CLI post_tool payload from stdin and, when an editable file
was touched, appends a reminder to the tool output the model sees, so the
review baseline stays current. Best effort only: the hook runs in its own
process and cannot inspect the MCP server's in-memory baseline.
"""

import json
import sys


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    if not isinstance(payload, dict) or payload.get("tool_status") != "success":
        return
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return
    path = tool_input.get("file_path") or tool_input.get("path") or tool_input.get("filename")
    if not isinstance(path, str) or not path.strip():
        return
    reminder = (
        f"Aletheia: '{path}' was just edited. If it is not yet in the review "
        "baseline, call record_baseline with this path now, so the user can "
        "review your edits in the Aletheia web UI."
    )
    print(json.dumps({"hook_specific_output": {"additional_context": reminder}}))


if __name__ == "__main__":
    main()
'''


def git_root(directory: Path) -> Path | None:
    """The git repository root containing `directory`, if any.

    Vibe's `AGENTS.md` discovery walks up to the trusted folder's root, and
    project hooks load from the project folder. Installing at the git root
    mirrors the epinoia rule for host configuration (.opencode, .vibe): a
    subdirectory install may be invisible to the tool.
    """
    try:
        output = subprocess.run(  # noqa: S603 - invoking git by name is the point here
            ["git", "-C", str(directory), "rev-parse", "--show-toplevel"],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError:
        return None
    return Path(output.stdout.strip()).resolve()


def server_command(launched_by_uvx: bool = False) -> tuple[str, list[str]]:
    """The stdio command Vibe should use to launch this installation.

    When `aletheia setup` itself ran through `uvx` / `uv tool run`, the
    temporary environment it used is destroyed on exit, so Vibe must launch
    the server through `uvx` too. Otherwise the installed `aletheia` script
    (the README's venv/`pipx`-style install) is used directly.
    """
    if launched_by_uvx:
        return UVX_COMMAND, list(UVX_ARGS)
    return LOCAL_COMMAND, list(LOCAL_ARGS)


# --- config.toml ------------------------------------------------------------


def _load_config(text: str) -> TOMLDocument:
    try:
        return tomlkit.parse(text)
    except Exception as error:
        msg = f"config.toml is not valid TOML: {error}"
        raise ValueError(msg) from error


def _is_own_server(server: object) -> bool:
    return isinstance(server, dict) and server.get("name") == SERVER_NAME


def _new_server(command: str, args: list[str]) -> Table:
    server = tomlkit.table()
    server["name"] = SERVER_NAME
    server["transport"] = STDIO
    server["command"] = command
    server["args"] = args
    # Inline so it renders `env = { }` like the README, not a `[..env]` table.
    server["env"] = tomlkit.inline_table()
    return server


def _append_server(table: AoT, server: Table) -> None:
    """Append a server, with a blank line separating it from earlier ones."""
    table.append(server)
    if len(table) > 1:
        table[-1].trivia.indent = "\n"


def _upsert(table: AoT, command: str, args: list[str]) -> None:
    """Add or update our server in an MCP server array of tables."""
    match = next((server for server in table if _is_own_server(server)), None)
    if match is None:
        _append_server(table, _new_server(command, args))
        return
    # Never retarget an entry the user pointed elsewhere. Only stdio entries
    # describe how to launch a process; an http entry named `aletheia` is the
    # user's own choice and is left untouched.
    if match.get("transport") != STDIO:
        return
    if match.get("command") != command:
        match["command"] = command
    if "args" not in match or [str(arg) for arg in match["args"]] != args:
        match["args"] = args


def merge_mcp_server(text: str, command: str, args: list[str]) -> str:
    """Register the aletheia stdio MCP server, keeping the file's layout.

    Supports top-level `[[mcp_servers]]`, nested
    `[[model_providers.mcp_servers]]` inside a `[model_providers.<name>]`
    table, `[mcp_servers.<name>]` subtables, and no `mcp_servers` key at all
    (a top-level `[[mcp_servers]]` block is appended). An existing aletheia
    stdio entry is reused, and only its command/args are updated.
    """
    doc = _load_config(text)
    servers = doc.get("mcp_servers")
    if isinstance(servers, AoT):
        _upsert(servers, command, args)
        return tomlkit.dumps(doc)
    if isinstance(servers, Table):
        _upsert_named(servers, command, args)
        return tomlkit.dumps(doc)

    for _, section in doc.items():
        if not isinstance(section, Table):
            continue
        for _, provider in section.items():
            if not isinstance(provider, Table):
                continue
            nested = provider.get("mcp_servers")
            if not isinstance(nested, AoT):
                continue
            _upsert(nested, command, args)
            return tomlkit.dumps(doc)

    top_level = tomlkit.aot()
    _append_server(top_level, _new_server(command, args))
    if text.strip():
        top_level[0].trivia.indent = "\n"
    doc["mcp_servers"] = top_level
    return tomlkit.dumps(doc)


def _upsert_named(table: Table, command: str, args: list[str]) -> None:
    """Update our `[mcp_servers.aletheia]` subtable, or add it."""
    existing = table.get(SERVER_NAME)
    if isinstance(existing, dict):
        if existing.get("transport") == STDIO:
            existing["command"] = command
            existing["args"] = args
        return
    table[SERVER_NAME] = _new_server(command, args)


def merge_disabled_tools(text: str, tools: tuple[str, ...] = BUILTIN_TOOLS) -> str:
    """Forbid Vibe's built-in file-editing tools, keeping existing entries.

    Adds a top-level `disabled_tools` array or extends an existing one; other
    values (and their formatting, e.g. one item per line) are preserved, so
    `disabled_tools` never drops a tool the user disabled.
    """
    doc = _load_config(text)
    current = doc.get("disabled_tools")
    if current is None:
        array = tomlkit.array()
        array.extend(tools)
        array.multiline(True)
        doc["disabled_tools"] = array
        return tomlkit.dumps(doc)
    if not isinstance(current, Array):
        msg = "config.toml defines disabled_tools, but it is not an array"
        raise TypeError(msg)
    missing = [tool for tool in tools if tool not in current]
    for tool in missing:
        current.append(tool)
    if missing:
        current.multiline(True)
    return tomlkit.dumps(doc)


# --- AGENTS.md --------------------------------------------------------------


def merge_agents_md(text: str) -> str:
    """Ensure the editing policy is in AGENTS.md, between its own markers.

    The section is appended when absent and replaced in place when present,
    so reruns converge and the surrounding user prose is never modified.
    """
    begin = text.find(AGENTS_BEGIN)
    end = text.find(AGENTS_END)
    if begin != -1 and end > begin:
        return text[:begin] + AGENTS_SECTION.rstrip("\n") + text[end + len(AGENTS_END) :]
    if not text:
        return AGENTS_SECTION
    separator = "" if text.endswith("\n\n") else "\n"
    return f"{text}{separator}{AGENTS_SECTION}"


# --- installation -----------------------------------------------------------


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def install(base_dir: Path, launched_by_uvx: bool = False) -> list[str]:
    """Apply the recommended setup under `base_dir` (a project or ~/.vibe).

    Writes `.vibe/config.toml` (MCP server + disabled built-ins) and
    `.vibe/AGENTS.md` (editing policy), returning one human-readable line per
    file that says whether it changed. Refuses to rewrite a config.toml that
    is not valid TOML rather than guess at its structure.
    """
    command, args = server_command(launched_by_uvx)
    vibe_dir = base_dir / ".vibe"
    messages: list[str] = []

    config_toml = vibe_dir / "config.toml"
    before = _read(config_toml)
    if before.strip():
        try:
            tomllib.loads(before)
        except tomllib.TOMLDecodeError as error:
            msg = f"{config_toml} is not valid TOML: {error}"
            raise ValueError(msg) from error
    after = merge_disabled_tools(merge_mcp_server(before, command, args))
    _persist(messages, config_toml, before, after)

    agents_md = vibe_dir / "AGENTS.md"
    before = _read(agents_md)
    _persist(messages, agents_md, before, merge_agents_md(before))
    return messages


def _persist(messages: list[str], path: Path, before: str, after: str) -> None:
    if after == before:
        messages.append(f"unchanged {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(after, encoding="utf-8")
    messages.append(f"{'updated' if before else 'created'} {path}")


# --- legacy reminder hook (fallback) ---------------------------------------


def install_hook(base_dir: Path) -> Path:
    """Install the reminder hook under `base_dir`; return hooks.toml.

    Kept for `--legacy-hook`. Merge-safe: an existing `hooks.toml` keeps its
    hooks; ours is appended only when its unique name is absent.
    """
    vibe_dir = base_dir / ".vibe"
    hooks_dir = vibe_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hooks_toml = vibe_dir / "hooks.toml"
    existing = _read(hooks_toml)
    if HOOK_NAME not in existing:
        block = HOOKS_TOML if not existing or existing.endswith("\n") else f"\n{HOOKS_TOML}"
        hooks_toml.write_text(existing + block, encoding="utf-8")
    (hooks_dir / "aletheia_baseline.py").write_text(HOOK_SCRIPT, encoding="utf-8")
    return hooks_toml
