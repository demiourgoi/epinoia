from aletheia_mcp.review.diffs import (
    CREATED_MARKER,
    DELETED_MARKER,
    has_text_change,
    unified_diff,
)


def test_created_marker() -> None:
    diff = unified_diff(None, "new = 1\n", "a.py")
    assert diff.startswith(CREATED_MARKER)


def test_deleted_marker() -> None:
    diff = unified_diff("old = 1\n", None, "a.py")
    assert diff.startswith(DELETED_MARKER)


def test_no_change_empty_diff() -> None:
    assert unified_diff("same\n", "same\n", "a.py") == ""
    assert not has_text_change("same\n", "same\n")


def test_diff_has_headers_and_lines() -> None:
    diff = unified_diff("a\n", "b\n", "a.py")
    assert "--- a.py (before)" in diff
    assert "+++ a.py (after)" in diff
    assert "-a" in diff and "+b" in diff
    assert has_text_change("a\n", "b\n")
