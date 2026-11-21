"""Command line entry point: `aletheia` runs the MCP server."""

from cyclopts import App

from aletheia_mcp import __version__
from aletheia_mcp.server import run as run_server

app = App(name="aletheia", help="MCP server for Zed-style asynchronous change review.", version=__version__)


@app.default
def run() -> None:
    """Run the MCP server (stdio transport)."""
    run_server()


if __name__ == "__main__":  # pragma: no cover
    app()
