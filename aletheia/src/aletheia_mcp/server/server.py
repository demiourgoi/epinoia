"""Aletheia MCP server: the FastMCP instance and its lifecycle.

Importing this module builds the `mcp` instance but does **not** initialize
any transport; the review web server is only started lazily, when a session
is opened. Tools register themselves on `mcp` when the tools package is
imported (see `aletheia_mcp.server`).
"""

from fastmcp import FastMCP

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
