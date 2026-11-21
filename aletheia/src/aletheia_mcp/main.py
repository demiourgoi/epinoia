"""Command line entry point: `aletheia` runs the MCP server."""

from pathlib import Path
from typing import Annotated

from cyclopts import App, Parameter

from aletheia_mcp import __version__
from aletheia_mcp.server import run as run_server
from aletheia_mcp.setup import install_hook

app = App(name="aletheia", help="MCP server for Zed-style asynchronous change review.", version=__version__)


@app.default
def run() -> None:
    """Run the MCP server (stdio transport)."""
    run_server()


@app.command
def setup(
    directory: Annotated[
        Path, Parameter(help="Project directory to install the hook into (ignored with --global).")
    ] = Path("."),
    global_: Annotated[
        bool, Parameter(["--global", "-g"], help="Install into ~/.vibe instead of the project.")
    ] = False,
) -> None:
    """Install the Vibe hook that reminds the agent to keep the baseline current."""
    base = Path.home() if global_ else directory
    hooks_toml = install_hook(base)
    print(f"Installed the aletheia-baseline reminder hook ({hooks_toml}).")


if __name__ == "__main__":  # pragma: no cover
    app()
