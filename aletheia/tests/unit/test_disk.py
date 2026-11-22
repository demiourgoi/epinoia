from pathlib import Path

import pytest

from aletheia_mcp.review import disk


def test_write_replaces_atomically(tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    f.write_text("old")
    disk.write_text(f, "new")
    assert f.read_text() == "new"
    assert not list(tmp_path.glob(".aletheia-*")), "temp files must be cleaned up"


def test_write_missing_parent_fails(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        disk.write_text(tmp_path / "nodir" / "a.txt", "x")


def test_write_error_leaves_original(tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    f.write_text("original")
    with pytest.raises(OSError):
        disk.write_text(tmp_path / "nodir" / "a.txt", "x")
    assert f.read_text() == "original"
    assert not list(tmp_path.glob(".aletheia-*"))


def test_delete(tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    f.write_text("x")
    disk.delete(f)
    assert not f.exists()
    disk.delete(f)  # idempotent: file already gone


def test_write_preserves_lines(tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    disk.write_text(f, "a\nb\n")
    assert f.read_text() == "a\nb\n"
