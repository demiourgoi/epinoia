import json
from pathlib import Path

import anyio
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from aletheia_mcp.review.service import ReviewService, set_service
from aletheia_mcp.review.sessions import SessionStore
from aletheia_mcp.server import mcp
from aletheia_mcp.settings import Settings


@pytest.fixture
def fresh_service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ReviewService:
    monkeypatch.chdir(tmp_path)
    service = ReviewService(SessionStore(max_sessions=10), Settings(host="127.0.0.1", port=8417))
    set_service(service)
    return service


def _call_tool(name: str, arguments: dict[str, object]) -> str:
    async def run() -> str:
        async with Client(mcp) as client:
            result = await client.call_tool(name, arguments)
            return result.content[0].text

    return anyio.run(run)


def _call_json(name: str, arguments: dict[str, object]) -> dict[str, object]:
    data: dict[str, object] = json.loads(_call_tool(name, arguments))
    return data


def test_record_then_open_review_flow(fresh_service: ReviewService) -> None:
    a = Path("a.py").resolve()
    a.write_text("original\n")
    record = _call_json("record_baseline", {"paths": ["a.py"]})
    assert record["recorded"] == [str(a)]
    a.write_text("edited\n")

    opened = _call_json("open_review", {"paths": ["a.py"]})
    assert opened["status"] == "pending"
    assert opened["files_changed"] == 1
    assert str(a) == opened["files"][0]["path"]  # type: ignore[index]
    assert opened["url"].startswith("http://127.0.0.1:8417/s/")  # type: ignore[union-attr]
    session_id = opened["session_id"]

    fresh_service.decide_file(str(session_id), 0, "reject")
    status = _call_json("get_review_status", {"session_id": session_id})
    assert status["status"] == "all_rejected"
    file0 = status["files"][0]  # type: ignore[index]
    assert file0["status"] == "rejected" and file0["reverted"] is True
    assert a.read_text() == "original\n"


def test_record_marker_for_creation(fresh_service: ReviewService) -> None:
    recorded = _call_json("record_baseline", {"paths": ["new.py"]})
    assert recorded["recorded"] == []
    assert recorded["marked_for_creation"] == [str(Path("new.py").resolve())]


def test_open_review_requires_baseline(fresh_service: ReviewService) -> None:
    Path("a.py").write_text("x")
    with pytest.raises(ToolError, match="record_baseline"):
        _call_tool("open_review", {"paths": ["a.py"]})


def test_record_baseline_rejects_directory(fresh_service: ReviewService) -> None:
    Path("d").mkdir()
    with pytest.raises(ToolError, match="directory"):
        _call_tool("record_baseline", {"paths": ["d"]})


def test_open_review_rejects_empty(fresh_service: ReviewService) -> None:
    with pytest.raises(ToolError):
        _call_tool("open_review", {"paths": []})


def test_unknown_session_status(fresh_service: ReviewService) -> None:
    with pytest.raises(ToolError, match="Unknown review session"):
        _call_tool("get_review_status", {"session_id": "does-not-exist"})
