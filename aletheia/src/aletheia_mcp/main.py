"""Command line entry point: `aletheia` runs the MCP server."""

import sys
from pathlib import Path
from typing import Annotated

from cyclopts import App, Parameter

from aletheia_mcp import __version__
from aletheia_mcp.server import run as run_server
from aletheia_mcp.setup import git_root, install, install_hook

app = App(name="aletheia", help="MCP server for Zed-style asynchronous change review.", version=__version__)


@app.default
def run() -> None:
    """Run the MCP server (stdio transport)."""
    run_server()


def _launched_by_uvx() -> bool:
    """Whether this process runs from a temporary `uvx` / `uv tool run` environment.

    uv unpacks such environments into `<cache>/archive-v0/` and runs the tool
    from there, so the interpreter path identifies the variant: the `uvx`
    form resolves packages on every run, the installed one does not.
    """
    return any(part.startswith("archive-v0") for part in Path(sys.executable).parts)


@app.command
def setup(
    directory: Annotated[
        Path,
        Parameter(help="Project directory whose git root receives the setup (ignored with --global)."),
    ] = Path("."),
    global_: Annotated[
        bool, Parameter(["--global", "-g"], help="Install into ~/.vibe instead of the project.")
    ] = False,
    legacy_hook: Annotated[
        bool, Parameter("--legacy-hook", help="Install the old best-effort reminder hook instead (not recommended).")
    ] = False,
) -> None:
    """Configure Mistral Vibe to route every edit through Aletheia.

    Registers the `aletheia` MCP server, disables Vibe's built-in `edit` and
    `write_file` tools, and adds the editing policy to the project's
    `AGENTS.md` (or `~/.vibe/AGENTS.md` with --global). Idempotent and
    merge-safe: other content in those files is preserved.
    """
    base = Path.home() if global_ else _project_base(directory)
    if legacy_hook:
        hooks_toml = install_hook(base)
        print(f"Installed the aletheia-baseline reminder hook ({hooks_toml}).")
        print("This fallback only nudges the agent; prefer the default `aletheia setup`.")
        return
    for message in install(base, launched_by_uvx=_launched_by_uvx()):
        print(message)
    print("Restart Vibe to pick up the new configuration.")


def _project_base(directory: Path) -> Path:
    resolved = directory.expanduser().resolve()
    base = git_root(resolved) or resolved
    if base != resolved:
        print(f"Installing at the git root ({base}), not {resolved}.")
    return base


if __name__ == "__main__":  # pragma: no cover
    app()
