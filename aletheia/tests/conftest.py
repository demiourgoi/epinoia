"""Shared fixtures. Each test gets a fresh service untouched by ambient env."""

from pathlib import Path

import pytest

from aletheia_mcp.review import service as service_module
from aletheia_mcp.review.service import ReviewService, set_service
from aletheia_mcp.settings import Settings


@pytest.fixture
def service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ReviewService:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(service_module.web_server, "ensure_running", lambda _settings: "http://127.0.0.1:12345")
    fresh = ReviewService(Settings(host="127.0.0.1"))
    set_service(fresh)
    return fresh
