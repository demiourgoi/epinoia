from pathlib import Path

import pytest

from aletheia_mcp.errors import (
    DiskEffectError,
    InvalidDecisionError,
    NotInBaselineError,
    UnsupportedFileError,
)
from aletheia_mcp.review.service import ReviewService


def test_record_and_status(service: ReviewService, tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("original\n")
    result = service.record_baseline(["a.py", "new.py"])
    assert result["url"] == "http://127.0.0.1:12345"
    assert result["recorded"] == [str(a)]
    assert result["marked_for_creation"] == [str(tmp_path / "new.py")]
    assert service.get_change_status()["files_in_baseline"] == 2


def test_status_kinds_and_changed(service: ReviewService, tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    b = tmp_path / "new.py"
    c = tmp_path / "gone.py"
    a.write_text("original\n")
    c.write_text("keep\n")
    service.record_baseline(["a.py", "new.py", "gone.py"])
    a.write_text("edited\n")
    Path(b).write_text("created\n")
    c.unlink()
    files = {file["path"]: file for file in service.get_change_status()["files"]}
    assert files[str(a)]["kind"] == "modified" and files[str(a)]["changed"] is True
    assert files[str(b)]["kind"] == "created" and files[str(b)]["changed"] is True
    assert files[str(c)]["kind"] == "deleted" and files[str(c)]["changed"] is True
    assert "baseline" not in files[str(a)] and "diff" not in files[str(a)]


def test_status_unchanged_file(service: ReviewService, tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("same\n")
    service.record_baseline(["a.py"])
    files = service.get_change_status()["files"]
    assert files[0]["changed"] is False


def test_remove_adopts_working_dir(service: ReviewService, tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("original\n")
    service.record_baseline(["a.py"])
    a.write_text("edited\n")
    result = service.remove_from_baseline(["a.py"])
    assert result["removed"] == [str(a)]
    assert result["files_in_baseline"] == 0
    assert a.read_text() == "edited\n"
    with pytest.raises(NotInBaselineError):
        service.get_change_status() if False else service.baselines.get(a)


def test_rollback_restores_then_removes(service: ReviewService, tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("original\n")
    service.record_baseline(["a.py"])
    a.write_text("agent edit\n")
    result = service.rollback_to_baseline(["a.py"])
    assert result["rolled_back"] == [str(a)]
    assert result["files_in_baseline"] == 0
    assert a.read_text() == "original\n"


def test_rollback_created_file_deletes(service: ReviewService, tmp_path: Path) -> None:
    a = tmp_path / "new.py"
    service.record_baseline(["new.py"])
    a.write_text("created\n")
    service.rollback_to_baseline(["new.py"])
    assert not a.exists()
    assert len(service.baselines) == 0


def test_rollback_missing_created_file(service: ReviewService, tmp_path: Path) -> None:
    service.record_baseline(["new.py"])
    service.rollback_to_baseline(["new.py"])
    assert len(service.baselines) == 0


def test_rollback_disk_failure_keeps_entry(
    service: ReviewService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import aletheia_mcp.review.disk as disk_module

    def boom(path: Path, content: str) -> None:
        raise OSError("read-only")

    a = tmp_path / "a.py"
    a.write_text("original\n")
    service.record_baseline(["a.py"])
    a.write_text("edit\n")
    monkeypatch.setattr(disk_module, "write_text", boom)
    with pytest.raises(DiskEffectError, match="rollback"):
        service.rollback_to_baseline(["a.py"])
    assert len(service.baselines) == 1
    assert a.read_text() == "edit\n"


def test_rollback_across_multiple_files_stops_at_failure(
    service: ReviewService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import aletheia_mcp.review.disk as disk_module

    write = disk_module.write_text
    calls: list[Path] = []

    def failing_write(path: Path, content: str) -> None:
        calls.append(path)
        if len(calls) > 1:
            raise OSError("read-only")
        write(path, content)

    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("a0\n")
    b.write_text("b0\n")
    service.record_baseline(["a.py", "b.py"])
    a.write_text("a1\n")
    b.write_text("b1\n")
    monkeypatch.setattr(disk_module, "write_text", failing_write)
    with pytest.raises(DiskEffectError):
        service.rollback_to_baseline(["a.py", "b.py"])
    paths = [str(path) for path in service.baselines.paths()]
    assert len(paths) == 1 and a.read_text() == "a0\n"


def test_write_file_content(service: ReviewService, tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("agent\n")
    service.record_baseline(["a.py"])
    service.write_file_content("a.py", "user tweak\n")
    assert a.read_text() == "user tweak\n"
    service.remove_from_baseline(["a.py"])
    with pytest.raises(NotInBaselineError):
        service.write_file_content("a.py", "not under review\n")


def test_operations_require_paths(service: ReviewService) -> None:
    for loader in (
        lambda: service.record_baseline([]),
        lambda: service.remove_from_baseline([]),
        lambda: service.rollback_to_baseline([]),
    ):
        with pytest.raises(InvalidDecisionError):
            loader()


def test_operations_on_unknown_paths(service: ReviewService, tmp_path: Path) -> None:
    with pytest.raises(NotInBaselineError):
        service.remove_from_baseline(["never.py"])
    with pytest.raises(NotInBaselineError):
        service.rollback_to_baseline(["never.py"])


def test_record_rejects_directory(service: ReviewService, tmp_path: Path) -> None:
    (tmp_path / "d").mkdir()
    with pytest.raises(UnsupportedFileError, match="directory"):
        service.record_baseline(["d"])


def test_review_payload_has_contents_and_diffs(service: ReviewService, tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("original\n")
    service.record_baseline(["a.py"])
    a.write_text("edited\n")
    payload = service.review_payload()
    file = payload["files"][0]
    assert file["baseline"] == "original\n"
    assert file["current"] == "edited\n"
    assert "-original" in file["diff"] and "+edited" in file["diff"]
    assert payload["url"] == "http://127.0.0.1:12345"


def test_rerecord_resets_round(service: ReviewService, tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("one\n")
    service.record_baseline(["a.py"])
    service.remove_from_baseline(["a.py"])
    a.write_text("two\n")
    service.record_baseline(["a.py"])
    assert service.baselines.get(a).content == "two\n"
    service.rollback_to_baseline(["a.py"])
    assert a.read_text() == "two\n"
