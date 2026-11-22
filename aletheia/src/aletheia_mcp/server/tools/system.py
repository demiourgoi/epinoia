"""Server health tools."""

from aletheia_mcp.server.server import mcp


@mcp.tool
def ping() -> str:
    """Check that the Aletheia MCP server is alive; returns 'pong'."""
    return "pong"
