from pathlib import Path

import pytest

from aletheia_mcp.errors import (
    EditFailedError,
    OutsideTrustedRootError,
    UnsupportedFileError,
)
from aletheia_mcp.review.baselines import BaselineStore
from aletheia_mcp.review.editing import apply_edit, contains
from aletheia_mcp.review.service import ReviewService


def test_unique_replacement_and_result_shape(service: ReviewService, tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("x = 1\n")
    result = service.edit_file("a.py", "x = 1", "x = 2")
    assert result["baseline_registered"] is True
    assert result["file"] == str(f)
    assert result["old_string"] == "x = 1" and result["new_string"] == "x = 2"
    assert f.read_text() == "x = 2\n"
    assert service.baselines.get(f).content == "x = 1\n"


def test_replace_all_counts_occurrences(service: ReviewService, tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("a\na\na\n")
    result = service.edit_file("a.py", "a", "b", replace_all=True)
    assert result["message"] and "3" in result["message"]
    assert (tmp_path / "a.py").read_text() == "b\nb\nb\n"


def test_ambiguous_match_rejected(service: ReviewService, tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("a\na\n")
    with pytest.raises(EditFailedError, match="2 times"):
        service.edit_file("a.py", "a", "b")


def test_no_match_rejected(service: ReviewService, tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x\n")
    with pytest.raises(EditFailedError, match="not found"):
        service.edit_file("a.py", "nope", "b")


def test_same_strings_rejected(service: ReviewService, tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x\n")
    with pytest.raises(EditFailedError, match="different"):
        service.edit_file("a.py", "x", "x")


def test_missing_file_rejected(service: ReviewService, tmp_path: Path) -> None:
    with pytest.raises(EditFailedError, match="does not exist"):
        service.edit_file("nope.py", "a", "b")


def test_directory_rejected(service: ReviewService, tmp_path: Path) -> None:
    (tmp_path / "d").mkdir()
    with pytest.raises(UnsupportedFileError, match="directory"):
        service.edit_file("d", "a", "b")


def test_failed_edit_never_registers_baseline(service: ReviewService, tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("x\n")
    with pytest.raises(EditFailedError):
        service.edit_file("a.py", "nope", "b")
    assert len(service.baselines) == 0
    result = service.edit_file("a.py", "x", "y")
    assert result["baseline_registered"] is True
    assert service.baselines.get(f).content == "x\n"


def test_repeated_edits_do_not_reanchor(service: ReviewService, tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("one\n")
    service.edit_file("a.py", "one", "two")
    service.edit_file("a.py", "two", "three")
    assert service.baselines.get(f).content == "one\n"
    assert service.edit_file("a.py", "three", "four")["baseline_registered"] is False


def test_decided_file_edit_starts_new_round(service: ReviewService, tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("v1\n")
    service.edit_file("a.py", "v1", "v2")
    service.remove_from_baseline([str(f)])  # the user approved v2
    result = service.edit_file(str(f), "v2", "v3")
    assert result["baseline_registered"] is True
    assert service.baselines.get(f).content == "v2\n"


def test_trusted_root_allows_subdirectory(service: ReviewService, tmp_path: Path) -> None:
    sub = tmp_path / "pkg"
    sub.mkdir()
    f = sub / "a.py"
    f.write_text("x\n")
    result = service.edit_file("pkg/a.py", "x", "y")
    assert result["file"] == str(f)


def test_rejects_dotdot_escape(service: ReviewService, tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.py"
    outside.write_text("x\n")
    try:
        with pytest.raises(OutsideTrustedRootError, match="outside the trusted project root"):
            service.edit_file(f"../{outside.name}", "x", "y")
    finally:
        outside.unlink()


def test_rejects_absolute_outside(service: ReviewService, tmp_path: Path) -> None:
    outside = tmp_path.parent / "far.py"
    outside.write_text("x\n")
    try:
        with pytest.raises(OutsideTrustedRootError, match="outside the trusted project root"):
            service.edit_file(str(outside), "x", "y")
    finally:
        outside.unlink()


def test_rejects_symlink_escape(service: ReviewService, tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-real.py"
    outside.write_text("x\n")
    inside = tmp_path / "link.py"
    inside.symlink_to(outside)
    try:
        with pytest.raises(OutsideTrustedRootError, match="outside the trusted project root"):
            service.edit_file("link.py", "x", "y")
    finally:
        inside.unlink()
        outside.unlink()


def test_contains_resolution(tmp_path: Path) -> None:
    root = tmp_path
    child = root / "x"
    child.mkdir()
    assert contains(root, child)
    assert contains(root, root)
    assert not contains(root, root.parent)


def test_apply_edit_direct(tmp_path: Path) -> None:
    store = BaselineStore()
    f = tmp_path / "dir" / "a.py"
    f.parent.mkdir()
    f.write_text("x = 1\n")
    result = apply_edit(root=tmp_path, store=store, file_path=str(f), old_string="x = 1", new_string="x = 2")
    assert result["baseline_registered"] is True
    assert f.read_text() == "x = 2\n"


def test_trusted_root_falls_back_to_working_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    from aletheia_mcp.review import editing as editing_module

    cwd = Path.cwd()
    monkeypatch.setattr(editing_module, "git_root", lambda _dir: None)
    assert editing_module.trusted_root(cwd) == cwd


def test_trusted_root_uses_git_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from aletheia_mcp.review import editing as editing_module

    monkeypatch.setattr(editing_module, "git_root", lambda _dir: tmp_path)
    assert editing_module.trusted_root(Path.cwd()) == tmp_path
