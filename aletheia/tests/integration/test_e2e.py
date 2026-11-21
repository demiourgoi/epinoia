"""End-to-end: the real loopback web server, tools, and disk effects."""

from __future__ import annotations

import json
import socket
import urllib.request
from pathlib import Path

import anyio
from fastmcp import Client

from aletheia_mcp.review.service import ReviewService, set_service
from aletheia_mcp.review.sessions import SessionStore
from aletheia_mcp.server import mcp
from aletheia_mcp.settings import Settings


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_full_review_over_real_http(tmp_path: Path, monkeypatch) -> None:
    port = free_port()
    settings = Settings(host="127.0.0.1", port=port, max_sessions=5)
    set_service(ReviewService(SessionStore(5), settings))
    monkeypatch.chdir(tmp_path)

    main = tmp_path / "Main.java"
    main.write_text("class Main {\n}\n")
    created = tmp_path / "app.py"

    async def agent_flow() -> str:
        async with Client(mcp) as client:
            await client.call_tool("record_baseline", {"paths": ["Main.java", "app.py"]})
            main.write_text("class Main {\n    int x = 1;\n}\n")
            created.write_text("print('hi')\n")
            opened = await client.call_tool("open_review", {"paths": ["Main.java", "app.py"]})
            return opened.content[0].text

    opened = json.loads(anyio.run(agent_flow))
    session_id = opened["session_id"]
    assert opened["url"] == f"http://127.0.0.1:{port}/s/{session_id}"
    assert opened["files_changed"] == 2

    base = f"http://127.0.0.1:{port}"

    def get_json(path: str) -> dict:
        with urllib.request.urlopen(base + path) as response:
            return json.loads(response.read())

    def post(path: str, body: dict) -> dict:
        request = urllib.request.Request(
            base + path, data=json.dumps(body).encode(), headers={"content-type": "application/json"}
        )
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())

    with urllib.request.urlopen(f"{base}/s/{session_id}") as page:
        assert page.status == 200
    assert get_json(f"/api/sessions/{session_id}")["status"] == "pending"

    # User edits the Java proposal and approves it.
    edited = "class Main {\n    int x = 2; // user tweak\n}\n"
    assert (
        post(f"/api/sessions/{session_id}/files/0/decision", {"action": "save_edit", "content": edited})["status"]
        == "edited"
    )
    assert post(f"/api/sessions/{session_id}/files/0/decision", {"action": "approve"})["status"] == "approved"
    assert main.read_text() == edited

    # User rejects the created file: creation is rolled back on disk.
    rejected = post(f"/api/sessions/{session_id}/files/1/decision", {"action": "reject"})
    assert rejected["reverted"] is True
    assert not created.exists()

    async def check_status() -> str:
        async with Client(mcp) as client:
            status = await client.call_tool("get_review_status", {"session_id": session_id})
            return status.content[0].text

    final = json.loads(anyio.run(check_status))
    assert final["status"] == "mixed"
    by_path = {file["path"]: file["status"] for file in final["files"]}
    assert by_path[str(main.resolve())] == "approved"
    assert by_path[str(created.resolve())] == "rejected"


def test_assets_importable_from_package() -> None:
    import importlib.resources

    dist = importlib.resources.files("aletheia_mcp").joinpath("webui/dist")
    assert dist.joinpath("index.html").is_file()
