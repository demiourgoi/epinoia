from pathlib import Path

import pytest

from aletheia_mcp.errors import (
    AlreadyDecidedError,
    InvalidDecisionError,
    UnknownSessionError,
)
from aletheia_mcp.review.sessions import (
    FileReview,
    ReviewSession,
    SessionStore,
    compute_session_id,
)


def make_session(files: list[FileReview], session_id: str = "s") -> ReviewSession:
    return ReviewSession(session_id=session_id, files=files)


def test_approve_keeps_disk(tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("edited")
    session = make_session([FileReview(f, "original", "edited")])
    assert session.decide(0, "approve").status == "approved"
    assert f.read_text() == "edited"
    assert session.status() == "all_approved"


def test_reject_restores_baseline(tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("agent edit")
    session = make_session([FileReview(f, "original", "agent edit")])
    review = session.decide(0, "reject")
    assert review.status == "rejected"
    assert review.reverted
    assert f.read_text() == "original"


def test_reject_created_file_deletes(tmp_path: Path) -> None:
    f = tmp_path / "new.py"
    f.write_text("brand new")
    session = make_session([FileReview(f, None, "brand new")])
    session.decide(0, "reject")
    assert not f.exists()


def test_reject_missing_created_file_is_idempotent(tmp_path: Path) -> None:
    f = tmp_path / "new.py"  # never created
    session = make_session([FileReview(f, None, None)])
    session.decide(0, "reject")
    assert not f.exists()


def test_save_edit_writes_and_stays_pending(tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("agent edit")
    session = make_session([FileReview(f, "original", "agent edit")])
    review = session.decide(0, "save_edit", content="user tweak")
    assert review.status == "edited"
    assert f.read_text() == "user tweak"
    assert session.status() == "pending"
    session.decide(0, "approve")
    assert f.read_text() == "user tweak"
    assert session.status() == "all_approved"


def test_decide_reject_after_edit_reverts_baseline(tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("agent edit")
    session = make_session([FileReview(f, "original", "agent edit")])
    session.decide(0, "save_edit", content="user tweak")
    session.decide(0, "reject")
    assert f.read_text() == "original"
    assert session.status() == "all_rejected"


def test_double_decision_rejected(tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("edit")
    session = make_session([FileReview(f, "orig", "edit")])
    session.decide(0, "approve")
    with pytest.raises(AlreadyDecidedError):
        session.decide(0, "reject")


def test_invalid_actions(tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("edit")
    session = make_session([FileReview(f, "orig", "edit")])
    with pytest.raises(InvalidDecisionError):
        session.decide(0, "explode")
    with pytest.raises(InvalidDecisionError):
        session.decide(0, "save_edit")
    with pytest.raises(InvalidDecisionError):
        session.decide(7, "approve")


def test_status_mixed_and_pending(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("a")
    b.write_text("b")
    session = make_session([FileReview(a, "a", "a"), FileReview(b, "old", "b")])
    assert session.status() == "pending"
    session.decide(0, "approve")
    session.decide(1, "save_edit", content="b")
    assert session.status() == "pending"
    session.decide(1, "reject")
    assert session.status() == "mixed"


def test_decide_all_skips_decided(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("x")
    b.write_text("y")
    session = make_session([FileReview(a, "x0", "x"), FileReview(b, "y0", "y")])
    session.decide(0, "approve")
    session.decide_all("reject")
    assert session.status() == "mixed"
    assert b.read_text() == "y0"


def test_session_id_deterministic(tmp_path: Path) -> None:
    files = [FileReview(tmp_path / "a.py", "1", "2")]
    first_id, _ = compute_session_id(files)
    second_id, _ = compute_session_id([FileReview(tmp_path / "a.py", "1", "2")])
    assert first_id == second_id
    assert len(first_id) == 12
    other, _ = compute_session_id([FileReview(tmp_path / "a.py", "1", "3")])
    assert other != first_id


def test_session_id_order_independent(tmp_path: Path) -> None:
    a = FileReview(tmp_path / "a.py", "1", "2")
    b = FileReview(tmp_path / "b.py", "x", "y")
    assert compute_session_id([a, b])[0] == compute_session_id([b, a])[0]


def test_store_reopen_same_diff_returns_same_session(tmp_path: Path) -> None:
    store = SessionStore(max_sessions=10)

    def files() -> list[FileReview]:
        return [FileReview(tmp_path / "a.py", "1", "2")]

    first = store.create(files())
    second = store.create(files())
    assert first is second


def test_store_collision_suffix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = SessionStore(max_sessions=10)
    a = FileReview(tmp_path / "a.py", "1", "2")
    b = FileReview(tmp_path / "a.py", "3", "2")
    digest, _ = compute_session_id([a])
    ids = iter([digest] * 4)

    def fake_compute(files: list[FileReview]) -> tuple[str, str]:
        # shortcut: force a digest collision (a truncated-SHA256 event) to
        # exercise the disambiguation branch deterministically.
        return next(ids), compute_session_id(files)[1]

    monkeypatch.setattr("aletheia_mcp.review.sessions.compute_session_id", fake_compute)
    first = store.create([a])
    second = store.create([b])
    assert first.session_id != second.session_id
    assert second.session_id.endswith("-2")
    assert store.get(first.session_id) is first
    assert store.get(second.session_id) is second


def test_store_evicts_oldest(tmp_path: Path) -> None:
    store = SessionStore(max_sessions=2)
    s1 = store.create([FileReview(tmp_path / "1.py", None, "1")])
    store.create([FileReview(tmp_path / "2.py", None, "2")])
    store.create([FileReview(tmp_path / "3.py", None, "3")])
    assert len(store) == 2
    with pytest.raises(UnknownSessionError):
        store.get(s1.session_id)
