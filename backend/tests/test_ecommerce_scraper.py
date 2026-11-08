"""The e-commerce comparison path, end to end, with the network stubbed.

The scraper's own extraction is not retested here: it came across unchanged and
is covered by its own fixtures. What these tests cover is everything the
migration introduced around it -- the registry, the intake rules, and the three
pipeline stages that behave differently when the input is a product listing.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.api.v1.agents.ecommerce_insight import EcommerceInsightAgent
from app.api.v1.agents.ecommerce_scout import EcommerceScoutAgent
from app.api.v1.agents.registry import get_agent
from app.models.project import ComparisonType, ProjectCreate
from app.scrapers import ScrapedProductRecord, ScraperError, get_scraper, platform_keys
from app.scrapers.daraz import DarazProductScraper, metrics

OWN_URL = "https://www.daraz.pk/products/our-kettle-i111-s111.html"
RIVAL_URL = "https://www.daraz.pk/products/their-kettle-i222-s222.html"

OWN_META: dict[str, Any] = {
    "product_name": "Acme Steel Kettle 1.5L",
    "price": 1799.0, "original_price": 2000.0, "discount_percent": 10.0,
    "rating": 4.2, "review_count": 120, "qa_count": 1,
    "description_word_count": 80, "description_length": 520,
    "spec_count": 3, "bullet_count": 2, "image_count": 3, "has_video": False,
    "content_completeness_score": 50.0, "brand": "No Brand", "is_branded": False,
    "title_word_count": 6, "title_keyword_count": 5,
    "category": "Home > Kitchen", "category_depth": 2,
    "variant_count": 1, "shipping_cost": 150.0, "stock_status": "in_stock",
    "seller_verified": False, "seller_name": "Acme Store",
    "review_sentiment_score": 0.1,
}

RIVAL_META: dict[str, Any] = {
    "product_name": "Westpoint Electric Kettle 1.7L Stainless Steel",
    "price": 1299.0, "original_price": 2000.0, "discount_percent": 35.0,
    "rating": 4.6, "review_count": 900, "qa_count": 22,
    "description_word_count": 310, "description_length": 2100,
    "spec_count": 12, "bullet_count": 9, "image_count": 8, "has_video": True,
    "content_completeness_score": 87.5, "brand": "Westpoint", "is_branded": True,
    "title_word_count": 16, "title_keyword_count": 13,
    "category": "Home > Kitchen > Kettles", "category_depth": 4,
    "variant_count": 4, "shipping_cost": 0.0, "stock_status": "in_stock",
    "seller_verified": True, "seller_name": "Westpoint Official",
    "review_sentiment_score": 0.6,
}


def _record(role: str, url: str, meta: dict[str, Any]) -> ScrapedProductRecord:
    return ScrapedProductRecord(
        role=role, platform="daraz", url=url, product_name=meta["product_name"],
        text_fields={
            "title": meta["product_name"],
            "description": "Durable stainless steel body with a fast boil element. " * 20,
            "specs": "\n".join(f"- Spec {i}: value {i}" for i in range(meta["spec_count"])),
            "review": "\n\n".join(f"[5/5] Good quality, quick delivery. #{i}" for i in range(5)),
            "promo_tags": "Best Seller" if role == "competitor" else "No promotional badges found on this listing.",
            "policy_text": "7 day return policy. 1 year brand warranty.",
            "category": meta["category"],
        },
        metadata=dict(meta), method="bs4", warnings=[],
        images=[
            {"url": f"https://static-01.daraz.pk/p/{role}-{index}.jpg", "position": index, "source": "gallery"}
            for index in range(1, (meta.get("image_count") or 1) + 1)
        ],
    )


@pytest.fixture
def stub_scraper(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replaces the network call, leaving every other layer real."""
    by_role = {"own": (OWN_URL, OWN_META), "competitor": (RIVAL_URL, RIVAL_META)}

    def fake_scrape(self: Any, url: str, role: str) -> ScrapedProductRecord:
        _, meta = by_role[role]
        return _record(role, url, meta)

    monkeypatch.setattr(DarazProductScraper, "scrape", fake_scrape)


# ------------------------------------------------------------------ registry


def test_daraz_and_alibaba_are_the_registered_platforms() -> None:
    assert platform_keys() == ["alibaba", "daraz"]
    assert get_scraper("daraz").label == "Daraz"
    assert get_scraper("alibaba").label == "Alibaba"


def test_unknown_platform_names_what_is_available() -> None:
    with pytest.raises(ScraperError, match="daraz"):
        get_scraper("amazon")


def test_canonical_url_drops_tracking_but_keeps_the_sku() -> None:
    # Copied out of search results, the same listing carries a different
    # tracking blob every time. Canonicalising is what makes two copies equal.
    messy = f"{OWN_URL}?clickTrackInfo=BIG&spm=a2a0e&skuId=99&lang=en"
    assert get_scraper("daraz").canonical_url(messy) == f"{OWN_URL}?skuId=99&lang=en"


def test_non_daraz_urls_are_refused() -> None:
    with pytest.raises(ScraperError, match="not a Daraz domain"):
        get_scraper("daraz").validate_url("https://www.amazon.com/dp/B0EXAMPLE")


# -------------------------------------------------------------------- intake


def _intake(**overrides: Any) -> dict[str, Any]:
    payload = {
        "brandName": "Acme",
        "brandDescription": "We sell small kitchen appliances direct to consumers online.",
        "industry": "ecommerce",
        "targetAudience": "Urban households buying kitchen appliances online",
        "objectives": ["Grow marketplace revenue"],
        "comparisonType": "ecommerce_product",
        "ecommercePlatform": "daraz",
        "brandWebsite": OWN_URL,
        "competitors": [{"name": "Westpoint", "landingPageUrl": RIVAL_URL}],
    }
    payload.update(overrides)
    return payload


def test_valid_ecommerce_intake_is_accepted() -> None:
    project = ProjectCreate.model_validate(_intake())
    assert project.comparison_type is ComparisonType.ECOMMERCE_PRODUCT
    assert project.ecommerce_platform == "daraz"


def test_ecommerce_intake_requires_the_users_own_listing() -> None:
    # Optional for a website comparison; without it here there is no baseline.
    with pytest.raises(ValueError, match="your own Daraz product link"):
        ProjectCreate.model_validate(_intake(brandWebsite=""))


def test_ecommerce_intake_requires_a_platform() -> None:
    with pytest.raises(ValueError, match="Choose an e-commerce platform"):
        ProjectCreate.model_validate(_intake(ecommercePlatform=None))


def test_ecommerce_intake_rejects_an_unregistered_platform() -> None:
    with pytest.raises(ValueError, match="not a supported platform"):
        ProjectCreate.model_validate(_intake(ecommercePlatform="amazon"))


def test_ecommerce_intake_rejects_a_link_from_another_marketplace() -> None:
    with pytest.raises(ValueError, match="not a Daraz domain"):
        ProjectCreate.model_validate(_intake(brandWebsite="https://www.amazon.com/dp/B0EXAMPLE"))


def test_ecommerce_intake_rejects_the_same_listing_on_both_sides() -> None:
    same_listing_different_tracking = f"{OWN_URL}?spm=a2a0e&clickTrackInfo=BIG"
    with pytest.raises(ValueError, match="same listing"):
        ProjectCreate.model_validate(
            _intake(competitors=[{"name": "Rival", "landingPageUrl": same_listing_different_tracking}])
        )


def test_website_intake_is_untouched_by_the_new_rules() -> None:
    project = ProjectCreate.model_validate(
        _intake(
            comparisonType="website",
            ecommercePlatform="daraz",   # stale value from the form
            brandWebsite="https://acme.example",
            competitors=[{"name": "Northbrew", "landingPageUrl": "https://northbrew.example"}],
        )
    )
    assert project.comparison_type is ComparisonType.WEBSITE
    # A platform on a non-e-commerce project would be dead data.
    assert project.ecommerce_platform is None


# ------------------------------------------------------------ agent dispatch


def test_ecommerce_projects_get_the_scraper_backed_agents() -> None:
    project = {"comparison_type": "ecommerce_product"}
    assert type(get_agent(2, project)).__name__ == "EcommerceScoutAgent"
    assert type(get_agent(3, project)).__name__ == "EcommercePreprocessAgent"
    assert type(get_agent(4, project)).__name__ == "EcommerceInsightAgent"
    # Stages 5-9 are shared; nothing about them changes.
    assert type(get_agent(6, project)).__name__ == "MockStrategistAgent"


def test_website_and_social_projects_get_their_own_scrapers() -> None:
    website = {"comparison_type": "website"}
    social = {"comparison_type": "social_media", "social_platform": "instagram"}
    assert type(get_agent(2, website)).__name__ == "WebsiteScoutAgent"
    assert type(get_agent(2, social)).__name__ == "SocialScoutAgent"
    # Stage 3 is shared between them; stages 4+ are still the defaults.
    assert type(get_agent(3, website)).__name__ == "SourcePreprocessAgent"
    assert type(get_agent(6, social)).__name__ == "MockStrategistAgent"


def test_the_seeded_demo_project_keeps_the_mock_agents() -> None:
    """Its links do not resolve: it exists to walk the stages with no network."""
    demo = {"comparison_type": "website", "is_demo": True}
    assert type(get_agent(2, demo)).__name__ == "MockScoutAgent"
    assert type(get_agent(2, None)).__name__ == "MockScoutAgent"


# ---------------------------------------------------------------- stage 2


def test_scout_returns_a_source_and_a_product_per_listing(stub_scraper: None) -> None:
    result = asyncio.run(EcommerceScoutAgent().run({
        "project_id": "proj_1",
        "project": {"ecommerce_platform": "daraz", "brand_website": OWN_URL},
        "competitors": [{"id": "comp_1", "name": "Westpoint", "landing_page_url": RIVAL_URL}],
    }))

    assert [source["kind"] for source in result.payload] == ["ecommerce_product"] * 2
    products = result.artifacts["ecommerce_products"]
    assert [product["role"] for product in products] == ["own", "competitor"]

    own, rival = products
    assert own["price"] == 1799.0 and rival["price"] == 1299.0
    # The full scraper output survives, not just the promoted columns.
    assert own["raw_metadata"]["review_sentiment_score"] == 0.1
    assert set(own["text_fields"]) >= {"title", "description", "specs", "review"}
    # Evidence cites the source row, so the citation resolves in the UI.
    assert own["source_id"] == result.payload[0]["id"]
    # No LLM was called, so the UI renders a dash rather than a zero.
    assert result.tokens_used is None and result.cost_usd is None

    # One image row per photo, tied to its listing, main image first.
    images = result.artifacts["ecommerce_product_images"]
    own_images = [row for row in images if row["product_id"] == own["id"]]
    assert len(own_images) == OWN_META["image_count"]
    assert [row["position"] for row in own_images] == list(range(1, len(own_images) + 1))
    assert [row["is_primary"] for row in own_images] == [True] + [False] * (len(own_images) - 1)
    assert all(row["project_id"] == "proj_1" for row in images)
    assert {row["product_id"] for row in images} == {own["id"], rival["id"]}


def test_scout_fails_the_stage_when_the_users_own_listing_cannot_be_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def only_competitor_works(self: Any, url: str, role: str) -> ScrapedProductRecord:
        if role == "own":
            raise ScraperError("Product not found (HTTP 404)")
        return _record(role, url, RIVAL_META)

    monkeypatch.setattr(DarazProductScraper, "scrape", only_competitor_works)

    with pytest.raises(ScraperError, match="404"):
        asyncio.run(EcommerceScoutAgent().run({
            "project_id": "proj_1",
            "project": {"ecommerce_platform": "daraz", "brand_website": OWN_URL},
            "competitors": [{"id": "comp_1", "name": "Westpoint", "landing_page_url": RIVAL_URL}],
        }))


def test_scout_keeps_going_when_one_of_several_competitors_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A rival we cannot read is a warning, not a failed run: the comparison
    still works on the ones we got."""
    def second_competitor_fails(self: Any, url: str, role: str) -> ScrapedProductRecord:
        if url == "https://www.daraz.pk/products/gone-i333-s333.html":
            raise ScraperError("Product not found (HTTP 404)")
        return _record(role, url, OWN_META if role == "own" else RIVAL_META)

    monkeypatch.setattr(DarazProductScraper, "scrape", second_competitor_fails)

    result = asyncio.run(EcommerceScoutAgent().run({
        "project_id": "proj_1",
        "project": {"ecommerce_platform": "daraz", "brand_website": OWN_URL},
        "competitors": [
            {"id": "comp_1", "name": "Westpoint", "landing_page_url": RIVAL_URL},
            {"id": "comp_2", "name": "Gone", "landing_page_url": "https://www.daraz.pk/products/gone-i333-s333.html"},
        ],
    }))

    assert len(result.artifacts["ecommerce_products"]) == 2   # own + the one that worked
    assert any("404" in warning for warning in result.warnings)


# ---------------------------------------------------------------- metrics


def test_every_parameter_group_is_compared() -> None:
    groups = metrics.compare_all(OWN_META, RIVAL_META)
    assert [group["letter"] for group in groups] == list("ABCDEFGH")


def test_a_cheaper_competitor_wins_the_price_row() -> None:
    groups = {g["key"]: g for g in metrics.compare_all(OWN_META, RIVAL_META)}
    price = next(row for row in groups["pricing"]["metrics"] if row["field"] == "price")
    # Lower is better for price, and the rival is cheaper.
    assert price["winner"] == "competitor"
    assert price["delta"] == 500.0
    assert "38%" in " ".join(groups["pricing"]["insights"])


def test_a_field_neither_side_reported_has_no_winner() -> None:
    groups = {g["key"]: g for g in metrics.compare_all({"price": 10.0}, {"price": 20.0})}
    rating = next(row for row in groups["social_proof"]["metrics"] if row["field"] == "rating")
    # Never defaulted to a tie: an unmeasured field is not a draw.
    assert rating["winner"] is None


def test_identical_listings_produce_ties_not_winners() -> None:
    groups = metrics.compare_all(OWN_META, OWN_META)
    assert all(
        row["winner"] in (None, "tie")
        for group in groups
        for row in group["metrics"]
    )


# ---------------------------------------------------------------- stage 4


def _insight(products: list[dict[str, Any]]) -> Any:
    return asyncio.run(EcommerceInsightAgent().run({
        "project_id": "proj_1",
        "project": {"ecommerce_platform": "daraz"},
        "ecommerce_products": products,
    }))


def _product(role: str, meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"prod_{role}", "project_id": "proj_1", "source_id": f"src_{role}",
        "platform": "daraz", "role": role,
        "url": OWN_URL if role == "own" else RIVAL_URL,
        "product_name": meta["product_name"], "raw_metadata": dict(meta),
    }


def test_a_losing_group_becomes_a_gap_with_evidence() -> None:
    result = _insight([_product("own", OWN_META), _product("competitor", RIVAL_META)])
    gaps = result.payload

    assert gaps, "a clearly weaker listing should raise gaps"
    categories = {gap["category"] for gap in gaps}
    assert {"pricing", "content", "social_engagement"} <= categories

    for gap in gaps:
        assert gap["evidence"], f"{gap['category']} shipped without a citation"
        assert 0.0 <= gap["confidence"] <= 1.0
        assert gap["decision"] == "pending"
        # Every citation points at a real source row.
        assert all(item["source_id"] == "src_competitor" for item in gap["evidence"])


def test_gaps_are_raised_once_per_category_not_once_per_competitor() -> None:
    """With several rivals the same weakness surfaces repeatedly. The reviewer
    wants one decision per problem."""
    result = _insight([
        _product("own", OWN_META),
        _product("competitor", RIVAL_META),
        {**_product("competitor", RIVAL_META), "id": "prod_c2", "source_id": "src_c2"},
    ])
    categories = [gap["category"] for gap in result.payload]
    assert len(categories) == len(set(categories))


def test_a_stronger_listing_raises_no_gaps() -> None:
    result = _insight([_product("own", RIVAL_META), _product("competitor", OWN_META)])
    assert result.payload == []
    assert any("no gaps" in warning for warning in result.warnings)


def test_comparison_needs_both_sides() -> None:
    result = _insight([_product("own", OWN_META)])
    assert result.payload == []
    assert result.warnings
