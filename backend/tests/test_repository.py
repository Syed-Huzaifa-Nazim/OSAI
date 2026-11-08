"""The in-memory repository.

The store is shared at class level because two different repository instances
touch it during one run: the one serving a request, and the one the background
pipeline worker builds for itself. If a write from one is invisible to the
other, the pipeline reports "7 gaps identified" and the gaps endpoint returns
an empty list, which is exactly what happened before these tests existed.
"""

from __future__ import annotations

from app.services import demo_data
from app.services.repository import MemoryRepository


def _worker() -> MemoryRepository:
    """Stands in for the background runner's repository."""
    return MemoryRepository("worker-user")


def _request() -> MemoryRepository:
    """Stands in for the repository serving the next HTTP request."""
    return MemoryRepository("request-user")


def test_gaps_written_by_one_instance_are_visible_to_another() -> None:
    project_id = demo_data.DEMO_PROJECT_ID
    rows = [
        {
            "id": "gap_test_1",
            "project_id": project_id,
            "title": "A gap the worker found",
            "description": "...",
            "category": "content",
            "priority": "high",
            "user_priority": None,
            "confidence": 0.8,
            "evidence": [],
            "opportunity": "...",
            "decision": "pending",
            "reviewer_note": None,
            "created_at": demo_data.iso(),
        }
    ]

    _worker().replace_gaps(project_id, rows)

    seen = _request().list_gaps(project_id)
    assert [gap["id"] for gap in seen] == ["gap_test_1"]


def test_sources_written_by_one_instance_are_visible_to_another() -> None:
    project_id = demo_data.DEMO_PROJECT_ID
    _worker().replace_sources(project_id, [])
    assert _request().list_sources(project_id) == []


def test_strategy_cleared_by_one_instance_is_gone_for_another() -> None:
    project_id = demo_data.DEMO_PROJECT_ID
    _worker().insert_strategy(
        {
            "id": "strategy_test_1",
            "project_id": project_id,
            "version": 1,
            "title": "Draft",
            "executive_summary": "...",
            "status": "awaiting_approval",
            "initiatives": [],
            "critic_feedback": [],
            "addressed_gap_ids": [],
            "generated_at": demo_data.iso(),
            "approved_at": None,
        }
    )
    assert _request().get_strategy(project_id) is not None

    _worker().clear_strategies(project_id)
    assert _request().get_strategy(project_id) is None


def test_deleting_a_project_removes_its_children_for_every_instance() -> None:
    project_id = demo_data.DEMO_PROJECT_ID
    assert _request().list_gaps(project_id)

    _worker().delete_project(project_id)

    assert _request().list_gaps(project_id) == []
    assert _request().list_competitors(project_id) == []
    assert _request().list_sources(project_id) == []
    assert _request().get_pipeline(project_id) is None


def test_reads_return_copies_so_a_caller_cannot_corrupt_the_store() -> None:
    project = _request().get_project(demo_data.DEMO_PROJECT_ID)
    project["brand_name"] = "Mutated"

    assert _request().get_project(demo_data.DEMO_PROJECT_ID)["brand_name"] != "Mutated"


def test_demo_project_is_seeded_parked_at_the_first_checkpoint() -> None:
    """The demo project has to open on the interesting state: stopped, waiting
    on a person."""
    state = _request().get_pipeline(demo_data.DEMO_PROJECT_ID)

    assert state is not None
    assert state["blocked_on"] == 5
    assert state["stages"]["4"]["status"] == "complete"
    assert state["stages"]["5"]["status"] == "awaiting_human"
    assert state["stages"]["6"]["status"] == "idle"
