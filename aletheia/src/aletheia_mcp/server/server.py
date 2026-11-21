"""Aletheia MCP server: the FastMCP instance and its lifecycle.

Importing this module builds the `mcp` instance but does **not** initialize
any transport; the review web server is only started lazily, when a session
is opened.
"""

from fastmcp import FastMCP

from aletheia_mcp.server.tools import system

mcp: FastMCP = FastMCP(
    "aletheia",
    instructions=(
        "Zed-style change review for terminal agents: record a baseline of the files "
        "you are about to edit, edit them (they are on disk and lintable), then call "
        "open_review and show the returned URL to the user. The review never blocks; "
        "rejections are rolled back on disk."
    ),
)


def run() -> None:
    """Run the MCP server on stdio (the transport CLI agents expect)."""
    mcp.run(transport="stdio")


__all__ = ["mcp", "run"]


def _register_tools() -> None:
    mcp.tool(system.ping)


_register_tools()
