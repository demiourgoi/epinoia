from importlib.metadata import entry_points
from importlib.metadata import version as pkg_version

import anyio
from fastmcp import Client

from aletheia_mcp.main import app
from aletheia_mcp.server import mcp


def test_version() -> None:
    assert pkg_version("epinoia-aletheia")


def test_console_script_registered() -> None:
    eps = entry_points()
    scripts = eps.select(group="console_scripts") if hasattr(eps, "select") else eps
    aletheia = [ep for ep in scripts if ep.name == "aletheia"]
    assert aletheia, "console script 'aletheia' must be registered"
    assert aletheia[0].value == "aletheia_mcp.main:app"


def test_main_app_is_cyclopts() -> None:
    assert app.name == ("aletheia",) and app.version == "0.1.0"


def test_ping_tool() -> None:
    async def call() -> object:
        async with Client(mcp) as client:
            return await client.call_tool("ping", {})

    result = anyio.run(call)
    assert result.content[0].text == "pong"
