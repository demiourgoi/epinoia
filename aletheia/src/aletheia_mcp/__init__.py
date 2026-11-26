"""Aletheia: an MCP server for Zed-style asynchronous change review."""

try:
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("epinoia-aletheia")
    except PackageNotFoundError:  # running from source without install
        __version__ = "0.0.0.dev0"
except Exception:  # pragma: no cover
    __version__ = "0.0.0.dev0"
