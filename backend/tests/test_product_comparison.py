"""Scrape-and-display for e-commerce comparisons, through the HTTP API.

The scraper's network call and Chroma are stubbed; routing, the scrape runner,
persistence and the comparison read-back are all real.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.scrapers.daraz import DarazProductScraper
from app.services import pipeline_service
from app.vectorstore import chroma
from tests.real_urls import DARAZ_DELL_MOUSE, DARAZ_HP_MOUSE
from tests.test_ecommerce_scraper import OWN_META, RIVAL_META, _record

INTAKE = {
    "brandName": "Dell wireless optical mouse",
    "brandWebsite": DARAZ_DELL_MOUSE,
    "brandDescription": "Wireless computer accessories.",
    "industry": "ecommerce",
    "objectives": ["Win the mouse category"],
    "comparisonType": "ecommerce_product",
    "ecommercePlatform": "daraz",
    "competitors": [{"name": "HP W10", "landingPageUrl": DARAZ_HP_MOUSE}],
}


@pytest.fixture
def stubbed(monkeypatch: pytest.MonkeyPatch) -> dict[str, list]:
    """No network, no vector store; records what would have been stored/queried."""
    calls: dict[str, list] = {"scraped": [], "stored": [], "queried": []}

    def fake_scrape(self: Any, url: str, role: str) -> Any:
        calls["scraped"].append((role, url))
        return _record(role, url, OWN_META if role == "own" else RIVAL_META)

    def fake_add_chunks(project_id, ids, documents, metadatas, embeddings=None):
        calls["stored"].extend(metadatas)
        return len(ids)

    def fake_query(project_id, text, n_results=8, where=None):
        calls["queried"].append(where)
        clauses = {k: v["$eq"] for c in where["$and"] for k, v in c.items()}
        return [{
            "document": f"{clauses['field_type']} passage for {clauses['product_id']}",
            "metadata": {"field_type": clauses["field_type"], "chunk_index": 0},
            "relevance": 0.8123,
        }]

    monkeypatch.setattr(DarazProductScraper, "scrape", fake_scrape)
    monkeypatch.setattr(chroma, "add_chunks", fake_add_chunks)
    monkeypatch.setattr(chroma, "query", fake_query)
    monkeypatch.setattr(chroma, "delete_collection", lambda project_id: None)
    return calls


def _create(client: TestClient) -> str:
    response = client.post("/api/v1/projects", json=INTAKE)
    assert response.status_code == 201, response.json()
    return response.json()["id"]


def _scrape(client: TestClient, project_id: str) -> None:
    """Starts the scrape, then runs the background job to completion.

    TestClient executes BackgroundTasks before returning, so the runner has
    already finished when the POST comes back.
    """
    response = client.post(f"/api/v1/scrapers/projects/{project_id}/scrape")
    assert response.status_code == 200, response.json()


def test_scrape_runs_only_the_scrape_stages(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client)
    _scrape(client, project_id)

    state = client.get(f"/api/v1/projects/{project_id}/pipeline").json()
    statuses = {int(stage_id): stage["status"] for stage_id, stage in state["stages"].items()}
    assert statuses[2] == "complete"
    assert statuses[3] == "complete"
    # Nothing from stage 4 on is touched: no gap analysis, no agents.
    assert all(statuses[stage_id] == "idle" for stage_id in range(4, 10))
    assert client.get(f"/api/v1/projects/{project_id}/gaps").json() == []

    project = client.get(f"/api/v1/projects/{project_id}").json()
    assert project["status"] == "complete"
    # The scraper was handed the links exactly as pasted.
    assert ("own", DARAZ_DELL_MOUSE) in stubbed["scraped"]
    assert ("competitor", DARAZ_HP_MOUSE) in stubbed["scraped"]


def test_starting_marks_the_scrape_running_before_the_job_picks_it_up(
    client: TestClient, stubbed: dict
) -> None:
    """A page that polls immediately after starting must see progress, not idle."""
    project_id = _create(client)
    from app.services.repository import get_repository

    state = pipeline_service.start_scrape(get_repository("demo-user-0001", ""), project_id)
    assert state["stages"]["2"]["status"] == "running"


def test_a_second_start_while_running_is_refused(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client)
    from app.services.repository import get_repository

    repo = get_repository("demo-user-0001", "")
    pipeline_service.start_scrape(repo, project_id)
    response = client.post(f"/api/v1/scrapers/projects/{project_id}/scrape")
    assert response.status_code == 409


def test_products_are_available_after_scraping(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client)
    _scrape(client, project_id)

    products = client.get(f"/api/v1/scrapers/projects/{project_id}/products").json()
    assert [p["role"] for p in products] == ["own", "competitor"]
    assert products[0]["price"] == 1799.0
    assert products[0]["chunkCount"] > 0


def test_products_carry_their_images_in_gallery_order(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client)
    _scrape(client, project_id)

    products = client.get(f"/api/v1/scrapers/projects/{project_id}/products").json()
    own, rival = products
    assert len(own["images"]) == OWN_META["image_count"]
    assert len(rival["images"]) == RIVAL_META["image_count"]
    assert [image["position"] for image in rival["images"]] == list(range(1, len(rival["images"]) + 1))
    assert rival["images"][0]["isPrimary"] is True
    assert all(image["productId"] == rival["id"] for image in rival["images"])
    assert own["images"][0]["url"].startswith("https://static-01.daraz.pk/")


def test_scraping_again_replaces_the_images(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client)
    _scrape(client, project_id)
    first = client.get(f"/api/v1/scrapers/projects/{project_id}/products").json()
    _scrape(client, project_id)
    second = client.get(f"/api/v1/scrapers/projects/{project_id}/products").json()

    # Same photo count, new rows: the old listing's images went with it.
    assert len(second[0]["images"]) == len(first[0]["images"])
    assert {i["id"] for i in second[0]["images"]}.isdisjoint({i["id"] for i in first[0]["images"]})


def test_a_listing_without_images_still_compares(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, stubbed: dict
) -> None:
    def no_photos(self: Any, url: str, role: str) -> Any:
        record = _record(role, url, OWN_META if role == "own" else RIVAL_META)
        record.images = []
        return record

    monkeypatch.setattr(DarazProductScraper, "scrape", no_photos)
    project_id = _create(client)
    _scrape(client, project_id)

    products = client.get(f"/api/v1/scrapers/projects/{project_id}/products").json()
    assert [p["images"] for p in products] == [[], []]
    assert client.get(f"/api/v1/scrapers/projects/{project_id}/comparison").status_code == 200


def test_failing_to_store_images_does_not_fail_the_scrape(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, stubbed: dict
) -> None:
    """E.g. the images migration has not been applied yet."""
    from app.services.repository import MemoryRepository

    def table_missing(self, project_id, rows):
        raise RuntimeError('relation "ecommerce_product_images" does not exist')

    monkeypatch.setattr(MemoryRepository, "replace_ecommerce_product_images", table_missing)
    project_id = _create(client)
    _scrape(client, project_id)

    state = client.get(f"/api/v1/projects/{project_id}/pipeline").json()
    assert state["stages"]["2"]["status"] == "complete"
    assert state["stages"]["3"]["status"] == "complete"
    assert client.get(f"/api/v1/scrapers/projects/{project_id}/comparison").status_code == 200


def test_listings_still_load_when_images_cannot_be_read(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, stubbed: dict
) -> None:
    project_id = _create(client)
    _scrape(client, project_id)
    from app.services.repository import MemoryRepository

    def table_missing(self, project_id):
        raise RuntimeError('relation "ecommerce_product_images" does not exist')

    monkeypatch.setattr(MemoryRepository, "list_ecommerce_product_images", table_missing)
    response = client.get(f"/api/v1/scrapers/projects/{project_id}/products")
    assert response.status_code == 200
    assert [p["images"] for p in response.json()] == [[], []]


def test_scoreboard_lists_every_parameter(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client)
    _scrape(client, project_id)

    groups = client.get(f"/api/v1/scrapers/projects/{project_id}/comparison").json()
    assert [g["letter"] for g in groups] == list("ABCDEFGH")
    pricing = groups[0]
    assert pricing["semanticFieldTypes"] == []
    assert pricing["competitorWins"] >= 1


def test_semantic_parameter_returns_passages_for_both_listings(
    client: TestClient, stubbed: dict
) -> None:
    project_id = _create(client)
    _scrape(client, project_id)

    detail = client.get(
        f"/api/v1/scrapers/projects/{project_id}/comparison/content_quality"
    ).json()
    assert detail["metadataOnly"] is False
    assert detail["parameter"]["label"] == "Content Quality"
    assert detail["parameter"]["insights"]
    assert detail["parameter"]["metrics"]

    for side in ("own", "competitor"):
        snippets = detail[side]["snippets"]
        # One search per text field the parameter covers: description and specs.
        assert {s["fieldType"] for s in snippets} == {"description", "specs"}
        assert all(s["score"] == 0.8123 for s in snippets)
        assert detail[side]["derived"]

    # Each search was scoped to one listing, so passages never cross sides.
    searched_products = {
        clause["product_id"]["$eq"]
        for where in stubbed["queried"]
        for clause in where["$and"]
        if "product_id" in clause
    }
    assert searched_products == {detail["own"]["productId"], detail["competitor"]["productId"]}


def test_metadata_only_parameter_does_not_search(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client)
    _scrape(client, project_id)

    detail = client.get(f"/api/v1/scrapers/projects/{project_id}/comparison/pricing").json()
    assert detail["metadataOnly"] is True
    assert detail["own"]["snippets"] == []
    assert stubbed["queried"] == []


def test_unknown_parameter_is_a_404(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client)
    _scrape(client, project_id)
    response = client.get(f"/api/v1/scrapers/projects/{project_id}/comparison/nonsense")
    assert response.status_code == 404


def test_comparison_before_scraping_is_a_404(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client)
    response = client.get(f"/api/v1/scrapers/projects/{project_id}/comparison")
    assert response.status_code == 404


def test_a_failed_scrape_is_recorded_for_a_retry(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, stubbed: dict
) -> None:
    from app.scrapers import ScraperError

    def always_404(self: Any, url: str, role: str) -> Any:
        raise ScraperError("Product not found (HTTP 404)")

    monkeypatch.setattr(DarazProductScraper, "scrape", always_404)
    project_id = _create(client)
    _scrape(client, project_id)

    state = client.get(f"/api/v1/projects/{project_id}/pipeline").json()
    assert state["stages"]["2"]["status"] == "error"
    # The scraper's own wording, which is written for the user.
    assert "HTTP 404" in state["stages"]["2"]["error"]
    assert client.get(f"/api/v1/projects/{project_id}").json()["status"] == "failed"

    # And it can be retried.
    monkeypatch.setattr(
        DarazProductScraper,
        "scrape",
        lambda self, url, role: _record(role, url, OWN_META if role == "own" else RIVAL_META),
    )
    _scrape(client, project_id)
    state = client.get(f"/api/v1/projects/{project_id}/pipeline").json()
    assert state["stages"]["2"]["status"] == "complete"
    assert state["stages"]["2"]["error"] is None


def test_the_agent_pipeline_cannot_be_started_on_an_ecommerce_project(
    client: TestClient, stubbed: dict
) -> None:
    project_id = _create(client)
    response = client.post(f"/api/v1/projects/{project_id}/scout/run")
    assert response.status_code == 409


def test_website_projects_cannot_be_scraped(client: TestClient, demo_project_id: str) -> None:
    response = client.post(f"/api/v1/scrapers/projects/{demo_project_id}/scrape")
    assert response.status_code == 409


def test_run_scrape_never_calls_an_agent_past_stage_3(
    client: TestClient, stubbed: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_id = _create(client)
    from app.services.repository import get_repository

    pipeline_service.start_scrape(get_repository("demo-user-0001", ""), project_id)
    stages_run: list[int] = []
    original = pipeline_service._run_stage

    async def spy(repo, pid, state, stage_id):
        stages_run.append(stage_id)
        return await original(repo, pid, state, stage_id)

    monkeypatch.setattr(pipeline_service, "_run_stage", spy)
    asyncio.run(pipeline_service.run_scrape(project_id, "demo-user-0001"))
    assert stages_run == [2, 3]


# ------------------------------------------------ Daraz gap analysis (stage 4) ---


def test_daraz_analysis_needs_both_listings_scraped(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client)
    response = client.post(f"/api/v1/projects/{project_id}/analysis/run")
    assert response.status_code == 409
    assert "scraped" in response.json()["error"]["message"].lower()


def test_daraz_analysis_stores_gaps_and_sends_the_standing_to_the_screen(
    client: TestClient, stubbed: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Find gaps on a scraped Daraz comparison: stage 4 runs the Daraz agent, the gaps are saved,
    the run parks at the review checkpoint, and the per-competitor results reach the API (metrics.daraz)."""
    from app.api.v1.agents.base import AgentResult
    from app.api.v1.agents.daraz_insight import DarazInsightAgent

    seen: dict[str, Any] = {}

    async def fake_run(self: Any, context: dict[str, Any]) -> AgentResult:
        seen["roles"] = sorted(p["role"] for p in context["ecommerce_products"])
        gap = {"id": "gap_daraz_1", "project_id": context["project_id"], "title": "Price: lower than the top listings",
               "description": "d", "category": "pricing", "priority": "medium", "confidence": 0.8, "evidence": [],
               "opportunity": "Try this: ...", "decision": "pending", "created_at": "2026-11-22T00:00:00Z",
               "details": {"kind": "daraz_price", "howSure": "Proven"}}
        part = {"competitor": "HP W10", "search_query": "wireless mouse",
                "standing": {"you": {"rank": 30}, "competitor": {"rank": 2}}, "comparison": [], "strengths": []}
        return AgentResult(payload=[gap], artifacts={"daraz_analysis": {"competitors": [part]}}, items_processed=1)

    monkeypatch.setattr(DarazInsightAgent, "run", fake_run)
    project_id = _create(client)
    _scrape(client, project_id)
    response = client.post(f"/api/v1/projects/{project_id}/analysis/run")
    assert response.status_code == 200, response.json()

    assert seen["roles"] == ["competitor", "own"]
    state = client.get(f"/api/v1/projects/{project_id}/pipeline").json()
    assert state["stages"]["4"]["status"] == "complete"
    assert state["blockedOn"] == 5
    daraz = state["stages"]["4"]["metrics"]["daraz"]
    assert daraz[0]["standing"]["competitor"]["rank"] == 2
    gaps = client.get(f"/api/v1/projects/{project_id}/gaps").json()
    assert [g["details"]["kind"] for g in gaps] == ["daraz_price"]
    assert client.get(f"/api/v1/projects/{project_id}").json()["status"] == "awaiting_review"
