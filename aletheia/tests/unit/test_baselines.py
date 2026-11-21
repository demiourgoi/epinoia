from pathlib import Path

import pytest

from aletheia_mcp.errors import (
    UnknownBaselineError,
    UnsupportedFileError,
)
from aletheia_mcp.review.baselines import BaselineStore, read_text_or_none


def test_read_existing_text(tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("x = 1\n")
    assert read_text_or_none(f) == "x = 1\n"


def test_read_missing_returns_none(tmp_path: Path) -> None:
    assert read_text_or_none(tmp_path / "nope.py") is None


def test_read_directory_rejected(tmp_path: Path) -> None:
    with pytest.raises(UnsupportedFileError, match="directory"):
        read_text_or_none(tmp_path)


def test_read_binary_rejected(tmp_path: Path) -> None:
    f = tmp_path / "blob.bin"
    f.write_bytes(b"\xff\xfe\x00binary")
    with pytest.raises(UnsupportedFileError, match="not valid UTF-8"):
        read_text_or_none(f)


def test_record_existing_and_marker(tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("original\n")
    missing = tmp_path / "new.py"
    store = BaselineStore()
    recorded = store.record([f, missing])
    assert recorded[f].content == "original\n"
    assert recorded[missing].content is None
    assert store.get(f).content == "original\n"
    assert store.get(missing).content is None


def test_record_overwrites(tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("one\n")
    store = BaselineStore()
    store.record([f])
    f.write_text("two\n")
    store.record([f])
    assert store.get(f).content == "two\n"
    assert len(store) == 1


def test_get_unknown_raises(tmp_path: Path) -> None:
    store = BaselineStore()
    with pytest.raises(UnknownBaselineError, match="record_baseline"):
        store.get(tmp_path / "never.seen")


def test_clear(tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("x\n")
    store = BaselineStore()
    store.record([f])
    store.clear()
    assert len(store) == 0
