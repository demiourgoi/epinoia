import json
from pathlib import Path

import anyio
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from aletheia_mcp.review import service as service_module
from aletheia_mcp.review.service import ReviewService, set_service
from aletheia_mcp.server import mcp
from aletheia_mcp.settings import Settings


@pytest.fixture
def fresh_service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ReviewService:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(service_module.web_server, "ensure_running", lambda _settings: "http://127.0.0.1:12345")
    service = ReviewService(Settings(host="127.0.0.1"))
    set_service(service)
    return service


def _call(name: str, arguments: dict[str, object]) -> str:
    async def run() -> str:
        async with Client(mcp) as client:
            result = await client.call_tool(name, arguments)
            return result.content[0].text

    return anyio.run(run)


def _call_json(name: str, arguments: dict[str, object]) -> dict[str, object]:
    data: dict[str, object] = json.loads(_call(name, arguments))
    return data


def test_full_agent_loop(fresh_service: ReviewService, tmp_path: Path) -> None:
    a = Path("a.py").resolve()
    a.write_text("original\n")
    record = _call_json("record_baseline", {"paths": ["a.py", "new.py"]})
    assert record["url"] == "http://127.0.0.1:12345"
    assert record["recorded"] == [str(a)]
    a.write_text("edited\n")
    Path("new.py").write_text("new\n")

    status = _call_json("get_change_status", {})
    assert status["files_in_baseline"] == 2
    kinds = {file["path"]: file["kind"] for file in status["files"]}
    assert kinds[str(a)] == "modified"

    approved = _call_json("remove_from_baseline", {"paths": ["a.py"]})
    assert approved["files_in_baseline"] == 1
    rejected = _call_json("rollback_to_baseline", {"paths": ["new.py"]})
    assert rejected["files_in_baseline"] == 0
    assert not Path("new.py").exists()
    assert a.read_text() == "edited\n"

    final = _call_json("get_change_status", {})
    assert final["files"] == []


def test_rejected_file_restores_content(fresh_service: ReviewService, tmp_path: Path) -> None:
    a = Path("a.py").resolve()
    a.write_text("original\n")
    _call_json("record_baseline", {"paths": ["a.py"]})
    a.write_text("wrong edit\n")
    _call_json("rollback_to_baseline", {"paths": ["a.py"]})
    assert a.read_text() == "original\n"


def test_missing_baseline_error(fresh_service: ReviewService, tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x")
    with pytest.raises(ToolError, match="record_baseline"):
        _call("remove_from_baseline", {"paths": ["a.py"]})


def test_empty_paths_rejected(fresh_service: ReviewService) -> None:
    with pytest.raises(ToolError, match="at least one file path"):
        _call("record_baseline", {"paths": []})


def test_directory_rejected(fresh_service: ReviewService, tmp_path: Path) -> None:
    (tmp_path / "d").mkdir()
    with pytest.raises(ToolError, match="directory"):
        _call("record_baseline", {"paths": ["d"]})


def test_edit_tool_full_agent_loop_without_record_baseline(fresh_service: ReviewService, tmp_path: Path) -> None:
    a = Path("doc.md").resolve()
    a.write_text("one\ntwo\n")

    edited = _call_json(
        "edit",
        {"file_path": str(a), "old_string": "one", "new_string": "ONE"},
    )
    assert edited["baseline_registered"] is True
    assert edited["file"] == str(a)
    assert edited["url"] == "http://127.0.0.1:12345"
    assert a.read_text() == "ONE\ntwo\n"

    again = _call_json(
        "edit",
        {"file_path": str(a), "old_string": "two", "new_string": "TWO"},
    )
    assert again["baseline_registered"] is False

    status = _call_json("get_change_status", {})
    assert status["files_in_baseline"] == 1
    file = status["files"][0]
    assert file["path"] == str(a)
    assert file["kind"] == "modified"
    assert file["changed"] is True

    rejected = _call_json("rollback_to_baseline", {"paths": [str(a)]})
    assert rejected["files_in_baseline"] == 0
    assert a.read_text() == "one\ntwo\n"


def test_edit_tool_creates_file_without_record_baseline(fresh_service: ReviewService, tmp_path: Path) -> None:
    created = _call_json(
        "edit",
        {"file_path": "draft.md", "old_string": "", "new_string": "# draft\n"},
    )
    assert created["created"] is True
    assert created["baseline_registered"] is True
    draft = Path("draft.md").resolve()
    assert draft.read_text() == "# draft\n"

    status = _call_json("get_change_status", {})
    assert status["files_in_baseline"] == 1
    file = status["files"][0]
    assert file["path"] == str(draft)
    assert file["kind"] == "created"

    rejected = _call_json("rollback_to_baseline", {"paths": ["draft.md"]})
    assert rejected["files_in_baseline"] == 0
    assert not draft.exists()

    with pytest.raises(ToolError):
        _call("edit", {"file_path": "draft.md", "old_string": "old", "new_string": "new"})


def test_edit_tool_ambiguous_match_is_tool_error(fresh_service: ReviewService, tmp_path: Path) -> None:
    a = Path("dup.py").resolve()
    a.write_text("a\na\n")
    with pytest.raises(ToolError):
        _call("edit", {"file_path": str(a), "old_string": "a", "new_string": "b"})
