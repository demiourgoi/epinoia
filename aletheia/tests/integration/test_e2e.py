"""End-to-end: the real loopback web server, tools, and disk effects."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import anyio
from fastmcp import Client

from aletheia_mcp.review.service import ReviewService, set_service
from aletheia_mcp.server import mcp
from aletheia_mcp.settings import Settings


def test_full_review_over_real_http(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    review_service = ReviewService(Settings(host="127.0.0.1"))
    set_service(review_service)

    def _url() -> str:
        return review_service.get_change_status()["url"]

    def call_tool(name: str, arguments: dict[str, object]) -> str:
        async def run() -> str:
            async with Client(mcp) as client:
                result = await client.call_tool(name, arguments)
                return result.content[0].text

        return anyio.run(run)

    main = tmp_path / "Main.java"
    main.write_text("class Main {\n}\n")
    created = tmp_path / "app.py"

    record = json.loads(call_tool("record_baseline", {"paths": ["Main.java", "app.py"]}))
    base = record["url"]
    assert record["marked_for_creation"] == [str(created)]

    main.write_text("class Main {\n    int x = 1;\n}\n")
    created.write_text("print('hi')\n")

    def get_json(path: str) -> dict:
        with urllib.request.urlopen(base + path) as response:
            return json.loads(response.read())

    def post(path: str, body: dict, method: str = "POST") -> dict:
        request = urllib.request.Request(
            base + path,
            data=json.dumps(body).encode(),
            headers={"content-type": "application/json"},
            method=method,
        )
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())

    # GUI payload at the constant URL.
    with urllib.request.urlopen(base + "/") as page:
        assert page.status == 200
    payload = get_json("/api/review")
    kinds = {f["path"]: f["kind"] for f in payload["files"]}
    assert kinds[str(main)] == "modified" and kinds[str(created)] == "created"

    # Live drift reflects ongoing edits without re-recording.
    main.write_text("class Main {\n    int x = 2;\n}\n")
    assert get_json("/api/review")["files"][0]["current"] == "class Main {\n    int x = 2;\n}\n"

    # User edits the Java proposal and approves it: the tweak stays on disk.
    edited = "class Main {\n    int x = 3; // user tweak\n}\n"
    assert post("/api/content", {"path": str(main), "content": edited})["written"] is True
    assert post("/api/baseline/files", {"paths": [str(main)]}, method="DELETE")["removed"] == [str(main)]
    assert main.read_text() == edited
    status = json.loads(call_tool("get_change_status", {}))
    assert status["files_in_baseline"] == 1

    # User rejects the created file: creation is rolled back and review ends.
    assert post("/api/rollback", {"paths": [str(created)]})["rolled_back"] == [str(created)]
    assert not created.exists()
    final = json.loads(call_tool("get_change_status", {}))
    assert final["files"] == []
    assert final["url"] == base
