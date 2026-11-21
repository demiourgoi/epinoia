"""Install the Vibe baseline-reminder hook into a project.

Mirrors harold-mcp's skill setup: `aletheia setup` writes the hook
configuration and a standalone script. Installation is idempotent and
merge-safe: an existing `hooks.toml` keeps its hooks; ours is appended only
when its unique name is absent.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

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
"""Aletheia baseline reminder hook (installed by `aletheia setup`).

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

    Vibe loads project-level hooks from the trusted project folder, and a
    session is typically rooted at the repository (the same discovery rule
    epinoia uses for opencode files: install at the git root, never inside
    a subdirectory, or the tool will not discover them).
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


def install_hook(base_dir: Path) -> Path:
    """Install the hook under `base_dir` (a project or ~/.vibe); return hooks.toml."""
    vibe_dir = base_dir / ".vibe"
    hooks_dir = vibe_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hooks_toml = vibe_dir / "hooks.toml"
    existing = hooks_toml.read_text(encoding="utf-8") if hooks_toml.exists() else ""
    if HOOK_NAME not in existing:
        block = HOOKS_TOML if not existing or existing.endswith("\n") else f"\n{HOOKS_TOML}"
        hooks_toml.write_text(existing + block, encoding="utf-8")
    script = hooks_dir / "aletheia_baseline.py"
    script.write_text(HOOK_SCRIPT, encoding="utf-8")
    return hooks_toml
