import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from aletheia_mcp.review.service import get_service
from aletheia_mcp.web.app import DIST_DIR, create_app


@pytest.fixture
def client(service) -> TestClient:
    return TestClient(create_app())


def test_review_payload(client: TestClient, tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("original\n")
    get_service().record_baseline(["a.py", "new.py"])
    a.write_text("edited\n")
    (tmp_path / "new.py").write_text("hello\n")
    resp = client.get("/api/review")
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload["files"]) == 2
    rounds = {file["path"]: file for file in payload["files"]}
    assert rounds[str(a)]["kind"] == "modified"
    assert rounds[str(a)]["changed"] is True
    assert rounds[str(tmp_path / "new.py")]["kind"] == "created"
    assert "-original" in rounds[str(a)]["diff"]


def test_add_to_baseline(client: TestClient, tmp_path: Path) -> None:
    (tmp_path / "b.py").write_text("b\n")
    resp = client.post("/api/baseline/files", json={"paths": ["b.py"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["recorded"] == [str(tmp_path / "b.py")]
    assert body["url"] == "http://127.0.0.1:12345"


def test_remove_approves(client: TestClient, tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("agent\n")
    get_service().record_baseline(["a.py"])
    resp = client.request("DELETE", "/api/baseline/files", json={"paths": ["a.py"]})
    assert resp.status_code == 200
    assert a.read_text() == "agent\n"
    assert get_service().get_change_status()["files_in_baseline"] == 0


def test_rollback_rejects(client: TestClient, tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("original\n")
    get_service().record_baseline(["a.py"])
    a.write_text("agent\n")
    resp = client.post("/api/rollback", json={"paths": ["a.py"]})
    assert resp.status_code == 200
    assert a.read_text() == "original\n"
    assert get_service().get_change_status()["files_in_baseline"] == 0


def test_rollback_all_and_approve_all_compose(client: TestClient, tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("a0\n")
    b.write_text("b0\n")
    get_service().record_baseline(["a.py", "b.py"])
    a.write_text("a1\n")
    b.write_text("b1\n")
    paths = [file["path"] for file in get_service().get_change_status()["files"]]
    resp = client.post("/api/rollback", json={"paths": paths})
    assert resp.status_code == 200
    assert a.read_text() == "a0\n" and b.read_text() == "b0\n"


def test_save_content(client: TestClient, tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("agent\n")
    get_service().record_baseline(["a.py"])
    resp = client.post("/api/content", json={"path": "a.py", "content": "user\n"})
    assert resp.status_code == 200 and resp.json()["written"] is True
    assert a.read_text() == "user\n"
    # entry stays; the file is still under review and changed
    status = get_service().get_change_status()["files"][0]
    assert status["changed"] is True


def test_save_content_requires_baseline_entry(client: TestClient, tmp_path: Path) -> None:
    (tmp_path / "free.py").write_text("x\n")
    resp = client.post("/api/content", json={"path": "free.py", "content": "y\n"})
    assert resp.status_code == 404


def test_unknown_path_404(client: TestClient) -> None:
    assert client.request("DELETE", "/api/baseline/files", json={"paths": ["nope.py"]}).status_code == 404
    assert client.post("/api/rollback", json={"paths": ["nope.py"]}).status_code == 404


def test_bad_payload_400(client: TestClient) -> None:
    assert client.post("/api/baseline/files", json={"paths": []}).status_code == 400
    assert client.request("DELETE", "/api/baseline/files", json={"paths": "notalist"}).status_code == 400
    assert (
        client.post(
            "/api/content",
            content=b"{",
            headers={"content-type": "application/json"},
        ).status_code
        == 400
    )
    assert client.post("/api/content", json={"path": "a"}).status_code == 400


def test_review_page_served(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200


def test_built_gui_is_packaged() -> None:
    index = DIST_DIR / "index.html"
    assert index.exists(), "run `make webui` and commit src/aletheia_mcp/webui/dist"
    assert (DIST_DIR / "assets").exists()
    assert "aletheia" in index.read_text().lower()


def test_mutating_routes_require_json_content_type(client: TestClient) -> None:
    resp = client.post(
        "/api/baseline/files",
        content=json.dumps({"paths": ["x"]}),
        headers={"content-type": "text/plain"},
    )
    assert resp.status_code == 403
    assert "Content-Type" in resp.json()["error"]


def test_cross_origin_requests_rejected(client: TestClient) -> None:
    for header in ("origin", "referer"):
        resp = client.post(
            "/api/baseline/files",
            json={"paths": ["x"]},
            headers={header: "https://evil.example.com/page"},
        )
        assert resp.status_code == 403
        assert header in resp.json()["error"]


def test_loopback_origin_allowed(client: TestClient, tmp_path: Path) -> None:
    (tmp_path / "ok.txt").write_text("x\n")
    resp = client.post(
        "/api/baseline/files",
        json={"paths": ["ok.txt"]},
        headers={"origin": "http://127.0.0.1:12345"},
    )
    assert resp.status_code == 200


def test_get_routes_skip_the_guard(client: TestClient) -> None:
    assert client.get("/api/review").status_code == 200


def test_root_redirects_to_review_page(client: TestClient) -> None:
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 307
    assert resp.headers["location"] == "/review"
    assert client.get("/review").status_code == 200
