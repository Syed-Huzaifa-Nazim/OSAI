"""Alibaba comparisons end to end, through the HTTP API.

Only Alibaba and Chroma are replaced. The listing fetch hands back real
(sanitised) listing records, so the scraper's matching and extraction, the
Scout and Preprocess stages, persistence, and the comparison read-back all run
as they do in production.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.scrapers.alibaba.scraper as scraper_module
from app.api.v1.agents.ecommerce_scout import EcommerceScoutAgent
from app.scrapers.alibaba.extract import TEXT_FIELD_TYPES
from app.scrapers.alibaba.listing import parse_listing
from app.scrapers.daraz import DarazProductScraper
from app.services.repository import MemoryRepository
from app.vectorstore import chroma
from tests.test_alibaba_scraper import (
    CHALLENGE_HTML,
    GAMING_ID,
    GAMING_URL,
    MOUSE_ID,
    MOUSE_URL,
    listing_page,
)
from tests.test_ecommerce_scraper import OWN_META, OWN_URL, RIVAL_META, RIVAL_URL, _record

B2B_COLUMNS = {"max_price", "moq", "moq_unit", "lead_time_days"}

INTAKE = {
    "brandName": "Kingmega mini mouse",
    "brandWebsite": MOUSE_URL,
    "brandDescription": "Wireless computer accessories for wholesale buyers.",
    "industry": "ecommerce",
    "objectives": ["Win wholesale mouse buyers"],
    "comparisonType": "ecommerce_product",
    "ecommercePlatform": "alibaba",
    "competitors": [{"name": "MLOONG MX302", "landingPageUrl": GAMING_URL}],
}


@pytest.fixture
def alibaba(monkeypatch: pytest.MonkeyPatch) -> dict[str, list]:
    """Every listing search finds both products; no Chroma, no network."""
    calls: dict[str, list] = {"listings": [], "stored": [], "queried": []}

    def fake_load_listing(page_url: str) -> tuple:
        calls["listings"].append(page_url)
        return parse_listing(listing_page(GAMING_ID, MOUSE_ID)), "bs4", []

    def fake_add_chunks(project_id, ids, documents, metadatas, embeddings=None):
        calls["stored"].extend(metadatas)
        return len(ids)

    def fake_query(project_id, text, n_results=8, where=None):
        calls["queried"].append(where)
        clauses = {k: v["$eq"] for c in where["$and"] for k, v in c.items()}
        return [{
            "document": f"{clauses['field_type']} passage for {clauses['product_id']}",
            "metadata": {"field_type": clauses["field_type"], "chunk_index": 0},
            "relevance": 0.71,
        }]

    monkeypatch.setattr(scraper_module, "_load_listing", fake_load_listing)
    monkeypatch.setattr(chroma, "add_chunks", fake_add_chunks)
    monkeypatch.setattr(chroma, "query", fake_query)
    monkeypatch.setattr(chroma, "delete_collection", lambda project_id: None)
    return calls


def _create(client: TestClient, **overrides: Any) -> Any:
    return client.post("/api/v1/projects", json={**INTAKE, **overrides})


def _error_text(response: Any) -> str:
    error = response.json()["error"]
    return " ".join([error["message"], *(error.get("fields") or {}).values()]).lower()


def _scraped_project(client: TestClient) -> str:
    response = _create(client)
    assert response.status_code == 201, response.json()
    project_id = response.json()["id"]
    # TestClient runs the background scrape before the response returns.
    assert client.post(f"/api/v1/scrapers/projects/{project_id}/scrape").status_code == 200
    return project_id


def _products(client: TestClient, project_id: str) -> list[dict[str, Any]]:
    response = client.get(f"/api/v1/scrapers/projects/{project_id}/products")
    assert response.status_code == 200, response.json()
    return response.json()


# -------------------------------------------------------------------- intake


def test_alibaba_is_offered_next_to_daraz(client: TestClient) -> None:
    platforms = {p["platform"]: p for p in client.get("/api/v1/scrapers/platforms").json()}
    assert set(platforms) == {"daraz", "alibaba"}
    assert platforms["alibaba"]["label"] == "Alibaba"
    assert "alibaba.com/product-detail/" in platforms["alibaba"]["urlExample"]


def test_an_alibaba_comparison_is_created(client: TestClient, alibaba: dict) -> None:
    response = _create(client)
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["comparisonType"] == "ecommerce_product"
    assert body["ecommercePlatform"] == "alibaba"


def test_a_link_from_another_marketplace_is_refused(client: TestClient) -> None:
    response = _create(client, brandWebsite=OWN_URL)
    assert response.status_code == 422
    assert "not an alibaba domain" in _error_text(response)


def test_an_alibaba_page_that_is_not_a_product_is_refused(client: TestClient) -> None:
    response = _create(
        client,
        competitors=[{"name": "Search page", "landingPageUrl": "https://www.alibaba.com/showroom/wireless-mouse.html"}],
    )
    assert response.status_code == 422
    assert "not a single product page" in _error_text(response)


@pytest.mark.parametrize(
    "same_product",
    [
        "https://m.alibaba.com/product/1601364965690/Mini-Wireless-Mouse.html",
        "https://www.alibaba.com/product-detail/Reworded-Title_1601364965690.html?spm=a2700.1",
    ],
)
def test_the_same_product_under_another_link_is_refused(client: TestClient, same_product: str) -> None:
    response = _create(client, competitors=[{"name": "Me again", "landingPageUrl": same_product}])
    assert response.status_code == 422
    assert "same listing" in _error_text(response)


def test_daraz_links_still_work_for_daraz(client: TestClient) -> None:
    response = _create(
        client,
        ecommercePlatform="daraz",
        brandWebsite=OWN_URL,
        competitors=[{"name": "Rival", "landingPageUrl": RIVAL_URL}],
    )
    assert response.status_code == 201, response.json()


# -------------------------------------------------------------------- scrape


def test_scraping_stores_both_listings_with_order_terms(client: TestClient, alibaba: dict) -> None:
    project_id = _scraped_project(client)

    state = client.get(f"/api/v1/projects/{project_id}/pipeline").json()
    assert state["stages"]["2"]["status"] == "complete", state["stages"]["2"]
    assert state["stages"]["3"]["status"] == "complete", state["stages"]["3"]
    assert client.get(f"/api/v1/projects/{project_id}").json()["status"] == "complete"

    own, rival = _products(client, project_id)
    assert (own["role"], rival["role"]) == ("own", "competitor")
    assert own["platform"] == rival["platform"] == "alibaba"
    assert own["url"] == (
        "https://www.alibaba.com/product-detail/Mini-Wireless-Mouse-Ergonomic-4-Buttons_1601364965690.html"
    )
    assert own["scrapeMethod"] == "bs4"
    assert (own["currency"], own["price"], own["maxPrice"]) == ("USD", 0.75, 0.77)
    assert (own["moq"], own["moqUnit"], own["leadTimeDays"]) == (100, "pieces", 5)
    assert (own["rating"], own["reviewCount"], own["imageCount"]) == (4.9, 15, 6)
    assert own["sellerName"] == "Guangzhou Kingmega Electronic Firm"
    assert own["rawMetadata"]["item_id"] == MOUSE_ID
    assert own["chunkCount"] > 0

    assert (rival["price"], rival["maxPrice"], rival["moq"], rival["moqUnit"]) == (9.5, 12.99, 1, "piece")
    assert rival["rawMetadata"]["item_id"] == GAMING_ID


def test_price_tiers_come_back_lowest_quantity_first(client: TestClient, alibaba: dict) -> None:
    own, rival = _products(client, _scraped_project(client))

    assert [(t["position"], t["minQuantity"], t["maxQuantity"], t["price"]) for t in own["priceTiers"]] == [
        (1, 100, 499, 0.77),
        (2, 500, 999, 0.76),
        (3, 1000, None, 0.75),
    ]
    assert {t["currency"] for t in own["priceTiers"]} == {"USD"}
    assert all(t["productId"] == own["id"] for t in own["priceTiers"])
    assert len(rival["priceTiers"]) == 4


def test_supplier_profiles_are_attached_to_their_listing(client: TestClient, alibaba: dict) -> None:
    own, rival = _products(client, _scraped_project(client))

    supplier = own["supplier"]
    assert supplier["productId"] == own["id"]
    assert supplier["name"] == "Guangzhou Kingmega Electronic Firm"
    assert (supplier["countryCode"], supplier["countryName"], supplier["yearsOnPlatform"]) == ("CN", "China", 2)
    assert (supplier["goldSupplier"], supplier["verified"], supplier["tradeAssurance"]) == (True, False, True)
    assert (supplier["responseRate"], supplier["historicOrderCount"]) == (98.2, 207)
    assert supplier["historicGmvLabel"] == "$70,000+"
    assert rival["supplier"]["verified"] is True


def test_product_images_are_stored_like_darazs(client: TestClient, alibaba: dict) -> None:
    own, _ = _products(client, _scraped_project(client))
    assert len(own["images"]) == 6
    assert [image["position"] for image in own["images"]] == [1, 2, 3, 4, 5, 6]
    assert [image["isPrimary"] for image in own["images"]] == [True] + [False] * 5
    assert own["images"][0]["url"] == "https://s.alicdn.com/@sc04/kf/Hfdceac95980345cb81a69168a387e0b1b.jpg"


def test_every_alibaba_text_field_is_embedded(client: TestClient, alibaba: dict) -> None:
    _scraped_project(client)
    embedded = {metadata["field_type"] for metadata in alibaba["stored"]}
    assert embedded == set(TEXT_FIELD_TYPES)
    assert {metadata["platform"] for metadata in alibaba["stored"]} == {"alibaba"}


def test_scraping_again_replaces_tiers_and_suppliers(client: TestClient, alibaba: dict) -> None:
    project_id = _scraped_project(client)
    first = _products(client, project_id)
    assert client.post(f"/api/v1/scrapers/projects/{project_id}/scrape").status_code == 200
    second = _products(client, project_id)

    assert len(second[0]["priceTiers"]) == len(first[0]["priceTiers"]) == 3
    assert {t["id"] for t in second[0]["priceTiers"]}.isdisjoint({t["id"] for t in first[0]["priceTiers"]})
    assert second[0]["supplier"]["id"] != first[0]["supplier"]["id"]
    # The old listings' profiles went with them: one per current listing.
    stored = [row for row in MemoryRepository._ecommerce_product_suppliers if row["project_id"] == project_id]
    assert sorted(row["product_id"] for row in stored) == sorted(product["id"] for product in second)


def test_a_blocked_listing_fails_the_scrape_with_the_reason(
    client: TestClient, alibaba: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        scraper_module, "_load_listing", lambda page_url: (parse_listing(CHALLENGE_HTML), "bs4", [])
    )
    response = _create(client)
    project_id = response.json()["id"]
    client.post(f"/api/v1/scrapers/projects/{project_id}/scrape")

    state = client.get(f"/api/v1/projects/{project_id}/pipeline").json()
    assert state["stages"]["2"]["status"] == "error"
    assert "does not bypass these checks" in state["stages"]["2"]["error"]
    assert client.get(f"/api/v1/projects/{project_id}").json()["status"] == "failed"


def test_failing_to_store_tiers_or_suppliers_does_not_fail_the_scrape(
    client: TestClient, alibaba: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E.g. migration 0004 has not been applied yet."""
    def table_missing(self, project_id, rows):
        raise RuntimeError('relation "ecommerce_product_price_tiers" does not exist')

    monkeypatch.setattr(MemoryRepository, "replace_ecommerce_product_price_tiers", table_missing)
    monkeypatch.setattr(MemoryRepository, "replace_ecommerce_product_suppliers", table_missing)
    project_id = _scraped_project(client)

    state = client.get(f"/api/v1/projects/{project_id}/pipeline").json()
    assert state["stages"]["2"]["status"] == "complete"
    products = _products(client, project_id)
    assert [(p["priceTiers"], p["supplier"]) for p in products] == [([], None), ([], None)]
    assert len(client.get(f"/api/v1/scrapers/projects/{project_id}/comparison").json()) == 10


def test_listings_still_load_when_tiers_and_suppliers_cannot_be_read(
    client: TestClient, alibaba: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_id = _scraped_project(client)

    def table_missing(self, project_id):
        raise RuntimeError('relation "ecommerce_product_suppliers" does not exist')

    monkeypatch.setattr(MemoryRepository, "list_ecommerce_product_price_tiers", table_missing)
    monkeypatch.setattr(MemoryRepository, "list_ecommerce_product_suppliers", table_missing)
    products = _products(client, project_id)
    assert [(p["priceTiers"], p["supplier"]) for p in products] == [([], None), ([], None)]
    assert products[0]["moq"] == 100  # the columns on the listing itself are unaffected


# ---------------------------------------------------------------- comparison


def test_the_scoreboard_has_parameters_a_to_j(client: TestClient, alibaba: dict) -> None:
    groups = client.get(f"/api/v1/scrapers/projects/{_scraped_project(client)}/comparison").json()
    assert [g["letter"] for g in groups] == list("ABCDEFGHIJ")

    order_terms = next(g for g in groups if g["key"] == "order_terms")
    assert order_terms["label"] == "Order Terms & Bulk Pricing"
    moq = next(row for row in order_terms["metrics"] if row["field"] == "moq")
    assert (moq["own"], moq["competitor"], moq["winner"]) == (100, 1, "competitor")

    supplier = next(g for g in groups if g["key"] == "supplier_credibility")
    assert supplier["semanticFieldTypes"] == ["supplier"]
    assert supplier["competitorWins"] >= 1


def test_a_b2b_parameter_returns_passages_from_its_own_text(client: TestClient, alibaba: dict) -> None:
    project_id = _scraped_project(client)
    detail = client.get(f"/api/v1/scrapers/projects/{project_id}/comparison/order_terms").json()

    assert detail["metadataOnly"] is False
    for side in ("own", "competitor"):
        assert {s["fieldType"] for s in detail[side]["snippets"]} == {"order_terms"}
        assert "entry_order_value" in detail[side]["derived"]


def test_a_metadata_only_parameter_does_not_search(client: TestClient, alibaba: dict) -> None:
    project_id = _scraped_project(client)
    detail = client.get(f"/api/v1/scrapers/projects/{project_id}/comparison/pricing").json()
    assert detail["metadataOnly"] is True
    assert alibaba["queried"] == []


# -------------------------------------------------------------- scout rows


def _scout(platform: str, own_url: str, rival_url: str) -> Any:
    return asyncio.run(EcommerceScoutAgent().run({
        "project_id": "proj_1",
        "project": {"ecommerce_platform": platform, "brand_website": own_url},
        "competitors": [{"id": "comp_1", "name": "Rival", "landing_page_url": rival_url}],
    }))


def test_alibaba_rows_carry_order_terms_tiers_and_suppliers(alibaba: dict) -> None:
    result = _scout("alibaba", MOUSE_URL, GAMING_URL)
    own, rival = result.artifacts["ecommerce_products"]

    assert {column: own[column] for column in B2B_COLUMNS} == {
        "max_price": 0.77, "moq": 100, "moq_unit": "pieces", "lead_time_days": 5,
    }
    tiers = result.artifacts["ecommerce_product_price_tiers"]
    assert [t["position"] for t in tiers if t["product_id"] == own["id"]] == [1, 2, 3]
    assert [t["position"] for t in tiers if t["product_id"] == rival["id"]] == [1, 2, 3, 4]
    suppliers = result.artifacts["ecommerce_product_suppliers"]
    assert [s["product_id"] for s in suppliers] == [own["id"], rival["id"]]
    assert all(s["project_id"] == "proj_1" for s in tiers + suppliers)


def test_daraz_rows_never_name_the_b2b_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    """So Daraz keeps working on a database where migration 0004 has not run."""
    monkeypatch.setattr(
        DarazProductScraper,
        "scrape",
        lambda self, url, role: _record(role, url, OWN_META if role == "own" else RIVAL_META),
    )
    result = _scout("daraz", OWN_URL, RIVAL_URL)

    for product in result.artifacts["ecommerce_products"]:
        assert not B2B_COLUMNS & set(product)
        assert product["currency"] == "PKR"
    assert result.artifacts["ecommerce_product_price_tiers"] == []
    assert result.artifacts["ecommerce_product_suppliers"] == []
