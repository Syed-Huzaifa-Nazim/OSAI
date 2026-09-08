"""Shared test fixtures.

Every test runs against the in-memory repository in demo mode, so the suite
needs no Supabase project, no network and no API keys.
"""

from __future__ import annotations

import os

import pytest

# Set before app.core.config is imported anywhere.
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("SUPABASE_URL", "")
os.environ.setdefault("SUPABASE_ANON_KEY", "")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.repository import MemoryRepository  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_store() -> None:
    """Re-seeds the in-memory store before each test so they cannot leak into
    one another."""
    MemoryRepository.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def demo_project_id() -> str:
    from app.services.demo_data import DEMO_PROJECT_ID

    return DEMO_PROJECT_ID
