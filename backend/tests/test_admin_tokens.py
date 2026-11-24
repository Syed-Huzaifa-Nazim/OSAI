"""Security gates and token lifecycle behavior without external services."""
from __future__ import annotations

import asyncio

from app.models.pipeline import StageStatus
from app.services import jobs, pipeline_service
from app.services.repository import MemoryRepository


def test_demo_identity_cannot_open_admin_or_mutate_tokens(client):
    assert client.get("/api/v1/admin/me").status_code == 403
    assert client.get("/api/v1/admin/users").status_code == 403
    assert client.post("/api/v1/admin/users/demo/tokens", json={"delta": 3, "reason": "test"}).status_code == 403
    assert client.post("/api/v1/tokens/requests", json={"amount": 2, "note": "test"}).status_code == 503


def test_completed_scrape_spends_once(monkeypatch, demo_project_id):
    repo = MemoryRepository("demo-user-0001")
    state = pipeline_service.empty_state(demo_project_id)
    repo.save_pipeline(demo_project_id, state)
    monkeypatch.setattr(pipeline_service, "get_worker_repository", lambda _: repo)
    monkeypatch.setattr(pipeline_service.token_service, "run_status", lambda _: "reserved")
    finishes = []
    monkeypatch.setattr(pipeline_service.token_service, "finish",
                        lambda run_id, success, reason=None: finishes.append((run_id, success)) or "spent")

    async def stage(repository, project_id, current, stage_id):
        current["stages"][str(stage_id)]["status"] = StageStatus.COMPLETE.value
        repository.save_pipeline(project_id, current)

    monkeypatch.setattr(pipeline_service, "_run_stage", stage)
    asyncio.run(pipeline_service.run_scrape(demo_project_id, repo.user_id, "run-id"))
    assert finishes == [("run-id", True)]
    assert repo.get_project(demo_project_id)["status"] == "complete"


def test_cancelled_scrape_is_not_spent(monkeypatch, demo_project_id):
    repo = MemoryRepository("demo-user-0001")
    repo.save_pipeline(demo_project_id, pipeline_service.empty_state(demo_project_id))
    monkeypatch.setattr(pipeline_service, "get_worker_repository", lambda _: repo)
    finishes = []
    monkeypatch.setattr(pipeline_service.token_service, "finish",
                        lambda *args: finishes.append(args))

    async def stage(repository, project_id, current, stage_id):
        raise jobs.JobCancelled(project_id)

    monkeypatch.setattr(pipeline_service, "_run_stage", stage)
    asyncio.run(pipeline_service.run_scrape(demo_project_id, repo.user_id, "run-id"))
    assert finishes == [("run-id", False, "Scrape cancelled")]
    assert repo.get_project(demo_project_id)["status"] != "complete"


def test_failed_scrape_releases_reservation(monkeypatch, demo_project_id):
    repo = MemoryRepository("demo-user-0001")
    repo.save_pipeline(demo_project_id, pipeline_service.empty_state(demo_project_id))
    monkeypatch.setattr(pipeline_service, "get_worker_repository", lambda _: repo)
    monkeypatch.setattr(pipeline_service.token_service, "run_status", lambda _: "reserved")
    finishes = []
    monkeypatch.setattr(pipeline_service.token_service, "finish",
                        lambda run_id, success, reason=None: finishes.append((run_id, success, reason)) or "released")

    async def failing_stage(*_):
        raise RuntimeError("scraper failed")

    monkeypatch.setattr(pipeline_service, "_run_stage", failing_stage)
    asyncio.run(pipeline_service.run_scrape(demo_project_id, repo.user_id, "run-id"))
    assert finishes == [("run-id", False, "scraper failed")]
    assert repo.get_project(demo_project_id)["status"] == "failed"
