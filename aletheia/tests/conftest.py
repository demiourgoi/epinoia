"""Shared fixtures. Each test gets fresh settings, untouched by ambient env."""

import pytest

from aletheia_mcp.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(host="127.0.0.1", port=8417, max_sessions=5)
