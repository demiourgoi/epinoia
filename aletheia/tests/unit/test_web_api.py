from pathlib import Path
from typing import NamedTuple

import pytest
from starlette.testclient import TestClient

from aletheia_mcp.review.service import ReviewService, set_service
from aletheia_mcp.review.sessions import SessionStore
from aletheia_mcp.settings import Settings
from aletheia_mcp.web.app import DIST_DIR, create_app


class Harness(NamedTuple):
    client: TestClient
    service: ReviewService
    session_id: str


@pytest.fixture
def harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Harness:
    monkeypatch.chdir(tmp_path)
    from aletheia_mcp.review import service as service_module

    monkeypatch.setattr(service_module.web_server, "ensure_running", lambda _settings: None)
    service = ReviewService(SessionStore(max_sessions=10), Settings(host="127.0.0.1", port=8417))
    set_service(service)
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("original\n")
    b.write_text("keep\n")
    service.record_baseline([str(a), str(b)])
    a.write_text("edited\n")
    b.write_text("edited-b\n")
    opened = service.open_review([str(a), str(b)])
    return Harness(TestClient(create_app()), service, str(opened["session_id"]))


def test_session_payload(harness: Harness, tmp_path: Path) -> None:
    resp = harness.client.get(f"/api/sessions/{harness.session_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending"
    file0 = body["files"][0]
    assert file0["path"].endswith("a.py")
    assert file0["baseline"] == "original\n"
    assert file0["current"] == "edited\n"
    assert "-original" in file0["diff"] and "+edited" in file0["diff"]


def test_approve_decision(harness: Harness) -> None:
    resp = harness.client.post(f"/api/sessions/{harness.session_id}/files/0/decision", json={"action": "approve"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    status = harness.client.get(f"/api/sessions/{harness.session_id}").json()
    assert status["status"] == "pending"  # file 1 still open


def test_reject_decision_reverts_disk(harness: Harness, tmp_path: Path) -> None:
    resp = harness.client.post(f"/api/sessions/{harness.session_id}/files/0/decision", json={"action": "reject"})
    assert resp.status_code == 200
    assert (tmp_path / "a.py").read_text() == "original\n"


def test_save_edit_writes_disk(harness: Harness, tmp_path: Path) -> None:
    resp = harness.client.post(
        f"/api/sessions/{harness.session_id}/files/1/decision",
        json={"action": "save_edit", "content": "user content\n"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "edited"
    assert (tmp_path / "b.py").read_text() == "user content\n"


def test_decide_all_approve(harness: Harness) -> None:
    resp = harness.client.post(f"/api/sessions/{harness.session_id}/decision", json={"action": "approve"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "all_approved"


def test_decide_all_reject(harness: Harness) -> None:
    resp = harness.client.post(f"/api/sessions/{harness.session_id}/decision", json={"action": "reject"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "all_rejected"


def test_already_decided_conflict(harness: Harness) -> None:
    id_url = f"/api/sessions/{harness.session_id}/files/0/decision"
    harness.client.post(id_url, json={"action": "approve"})
    resp = harness.client.post(id_url, json={"action": "reject"})
    assert resp.status_code == 409


def test_unknown_session_404(harness: Harness) -> None:
    assert harness.client.get("/api/sessions/does-not-exist").status_code == 404


def test_invalid_action_400(harness: Harness) -> None:
    resp = harness.client.post(f"/api/sessions/{harness.session_id}/files/0/decision", json={"action": "teleport"})
    assert resp.status_code == 400


def test_invalid_index_400(harness: Harness) -> None:
    resp = harness.client.post(f"/api/sessions/{harness.session_id}/files/zz/decision", json={"action": "approve"})
    assert resp.status_code == 400


def test_bad_json_400(harness: Harness) -> None:
    resp = harness.client.post(
        f"/api/sessions/{harness.session_id}/files/0/decision",
        content=b"{",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 400


def test_session_page_served(harness: Harness) -> None:
    resp = harness.client.get(f"/s/{harness.session_id}")
    assert resp.status_code == 200


def test_dist_dir_is_package_relative() -> None:
    assert DIST_DIR.name == "dist"
    assert DIST_DIR.parent.name == "webui"
    assert DIST_DIR.parent.parent.name == "aletheia_mcp"


def test_built_gui_is_packaged() -> None:
    index = DIST_DIR / "index.html"
    assert index.exists(), "run `make webui` and commit src/aletheia_mcp/webui/dist"
    assert (DIST_DIR / "assets").exists()
    assert "aletheia" in index.read_text().lower()


def test_decide_all_partial_failure_maps_500(harness: Harness, monkeypatch: pytest.MonkeyPatch) -> None:
    import aletheia_mcp.review.disk as disk_module

    write = disk_module.write_text
    calls: list[Path] = []

    def failing_write(path: Path, content: str) -> None:
        calls.append(path)
        if len(calls) > 1:
            raise OSError("read-only")
        write(path, content)

    monkeypatch.setattr(disk_module, "write_text", failing_write)
    resp = harness.client.post(f"/api/sessions/{harness.session_id}/decision", json={"action": "reject"})
    assert resp.status_code == 500
    # Earlier reverts stay applied; the failed file is still pending.
    session = harness.service.get_status(harness.session_id)
    statuses = {file["path"]: file["status"] for file in session["files"]}
    assert set(statuses.values()) == {"pending", "rejected"}
