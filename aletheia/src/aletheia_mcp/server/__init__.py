import aletheia_mcp.server.tools  # noqa: F401  (registers the tools on mcp)
from aletheia_mcp.server.server import mcp, run

__all__ = ["mcp", "run"]
