"""Aletheia MCP server: the FastMCP instance and its lifecycle.

Importing this module builds the `mcp` instance but does **not** initialize
any transport; the review web server is only started lazily, when the
first baseline is recorded. Tools register themselves on `mcp` when the
tools package is imported (see `aletheia_mcp.server`).
"""

from fastmcp import FastMCP

mcp: FastMCP = FastMCP(
    "aletheia",
    instructions=(
        "Zed-style change review for terminal agents. Protocol: BEFORE editing a file, "
        "record it with record_baseline (this also starts the review web server and "
        "returns the URL to show the user). Edit files normally - changes are on disk, "
        "so linters and tests run against them. The user reviews the live diff in the "
        "browser and approves or rejects files; decisions also arrive through the "
        "remove_from_baseline (approve) and rollback_to_baseline (reject) operations. "
        "Rejections restore pre-change content on disk; a re-edited file must be "
        "recorded again. Poll get_change_status() to see the drift; it never blocks."
    ),
)


def run() -> None:
    """Run the MCP server on stdio (the transport CLI agents expect)."""
    mcp.run(transport="stdio")


__all__ = ["mcp", "run"]
