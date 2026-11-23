"""Cancel a scrape or Find gaps: the run stops, nothing it read or found is saved, and the project is put back."""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.scrapers.daraz import DarazProductScraper
from app.services import pipeline_service
from app.services.repository import get_repository
from tests.test_ecommerce_scraper import OWN_META, RIVAL_META, _record
from tests.test_product_comparison import _create, _scrape, stubbed  # noqa: F401 - the fixture is used by name


def _repo():
    return get_repository("demo-user-0001", "")


def test_cancelling_a_rescrape_keeps_the_earlier_listings(
    client: TestClient, stubbed: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_id = _create(client)
    _scrape(client, project_id)                                    # a complete first scrape
    before = client.get(f"/api/v1/scrapers/projects/{project_id}/products").json()
    state_before = client.get(f"/api/v1/projects/{project_id}/pipeline").json()

    def cancelled_mid_scrape(self: Any, url: str, role: str) -> Any:
        pipeline_service.cancel_job(_repo(), project_id)           # the user presses Cancel while it reads
        changed = {**(OWN_META if role == "own" else RIVAL_META), "price": 1.0}
        return _record(role, url, changed)

    monkeypatch.setattr(DarazProductScraper, "scrape", cancelled_mid_scrape)
    _scrape(client, project_id)

    after = client.get(f"/api/v1/scrapers/projects/{project_id}/products").json()
    assert [p["price"] for p in after] == [p["price"] for p in before], "nothing from the cancelled run is saved"
    state = client.get(f"/api/v1/projects/{project_id}/pipeline").json()
    assert state["stages"]["3"]["status"] == state_before["stages"]["3"]["status"] == "complete"
    assert client.get(f"/api/v1/projects/{project_id}").json()["status"] == "complete"


def test_cancelling_find_gaps_keeps_the_earlier_gaps(
    client: TestClient, stubbed: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api.v1.agents.base import AgentResult
    from app.api.v1.agents.daraz_insight import DarazInsightAgent

    async def cancelled_analysis(self: Any, context: dict[str, Any]) -> AgentResult:
        pipeline_service.cancel_job(_repo(), context["project_id"])
        gap = {"id": "gap_x", "project_id": context["project_id"], "title": "t", "description": "d",
               "category": "pricing", "priority": "medium", "confidence": 0.8, "evidence": [], "opportunity": "o",
               "decision": "pending", "created_at": "2026-11-23T00:00:00Z", "details": {"kind": "daraz_price"}}
        return AgentResult(payload=[gap], items_processed=1)

    monkeypatch.setattr(DarazInsightAgent, "run", cancelled_analysis)
    project_id = _create(client)
    _scrape(client, project_id)
    assert client.post(f"/api/v1/projects/{project_id}/analysis/run").status_code == 200

    assert client.get(f"/api/v1/projects/{project_id}/gaps").json() == []
    state = client.get(f"/api/v1/projects/{project_id}/pipeline").json()
    assert state["stages"]["4"]["status"] == "idle" and state["blockedOn"] is None
    assert client.get(f"/api/v1/projects/{project_id}").json()["status"] == "complete"


def test_cancel_with_nothing_running_is_refused(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client)
    _scrape(client, project_id)
    response = client.post(f"/api/v1/projects/{project_id}/jobs/cancel")
    assert response.status_code == 409


def test_cancel_clears_a_run_left_stuck_by_a_server_restart(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client)
    _scrape(client, project_id)
    repo = _repo()
    state = pipeline_service.load_state(repo, project_id)
    state["stages"]["4"]["status"] = "running"                     # no job behind it any more
    repo.save_pipeline(project_id, state)
    repo.update_project(project_id, {"status": "running"})

    response = client.post(f"/api/v1/projects/{project_id}/jobs/cancel")
    assert response.status_code == 200
    assert response.json()["stages"]["4"]["status"] == "idle"
    assert client.get(f"/api/v1/projects/{project_id}").json()["status"] == "complete"


def test_a_cancelled_instagram_job_also_stops_the_apify_run() -> None:
    """Apify keeps running (and using credits) unless it is told to stop."""
    from app.scrapers.instagram import client as instagram
    from app.services import jobs

    aborted: list[str] = []

    class Run:
        def __init__(self, run_id: str) -> None:
            self.run_id = run_id

        def wait_for_finish(self, **_: Any) -> dict:
            jobs.cancel("proj_apify")                              # the user presses Cancel while Apify works
            return {"id": self.run_id, "status": "RUNNING"}

        def abort(self) -> None:
            aborted.append(self.run_id)

    class Actor:
        def start(self, run_input: dict) -> dict:
            return {"id": "run_1", "status": "RUNNING"}

    class Client:
        def actor(self, _: str) -> Actor:
            return Actor()

        def run(self, run_id: str) -> Run:
            return Run(run_id)

    jobs.begin("proj_apify", {"state": {}, "project": {}})
    token = jobs._current.set("proj_apify")
    try:
        with pytest.raises(jobs.JobCancelled):
            instagram._run_actor(Client(), {})
    finally:
        jobs._current.reset(token)
        jobs.finish("proj_apify")
    assert aborted == ["run_1"]


def test_a_job_that_crashes_is_recorded_not_left_running(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client)
    _scrape(client, project_id)
    repo = _repo()
    pipeline_service.start_analysis(repo, project_id)              # stage 4 marked running
    pipeline_service.record_crash(project_id, "demo-user-0001", [4], ConnectionError("database connection lost"))
    state = client.get(f"/api/v1/projects/{project_id}/pipeline").json()
    assert state["stages"]["4"]["status"] == "error" and "database connection lost" in state["stages"]["4"]["error"]
    assert client.get(f"/api/v1/projects/{project_id}").json()["status"] == "failed"
    assert client.post(f"/api/v1/projects/{project_id}/analysis/run").status_code == 200, "free to run again"
