"""Project creation and the stage-1 intake contract."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.real_urls import DARAZ_DELL_MOUSE, DARAZ_HP_MOUSE

VALID_PROJECT = {
    "brandName": "Test Brand",
    "brandWebsite": "https://testbrand.example",
    "brandDescription": "Analytics tooling for small product teams.",
    "industry": "saas",
    "targetAudience": "Small teams evaluating analytics tooling for the first time.",
    "objectives": ["Grow trial signups"],
    "competitors": [
        {
            "name": "Competitor One",
            "landingPageUrl": "https://competitor-one.example",
            "notes": None,
        }
    ],
}


def _post(client: TestClient, **overrides: Any) -> Any:
    return client.post("/api/v1/projects", json={**VALID_PROJECT, **overrides})


def _error_fields(response: Any) -> dict:
    return response.json()["error"].get("fields") or {}


def _error_text(response: Any) -> str:
    """Every message in the error envelope, lower-cased.

    Rules that span several fields (a link that has to match the chosen
    platform, say) are reported under ``body`` rather than one input.
    """
    error = response.json()["error"]
    return " ".join([error["message"], *_error_fields(response).values()]).lower()


def test_demo_project_is_listed(client: TestClient, demo_project_id: str) -> None:
    response = client.get("/api/v1/projects")
    assert response.status_code == 200

    projects = response.json()
    assert any(project["id"] == demo_project_id for project in projects)
    demo = next(project for project in projects if project["id"] == demo_project_id)
    # The demo project must badge itself, so a defence audience is never left
    # guessing whether the data is live.
    assert demo["isDemo"] is True


def test_create_project_returns_camel_case(client: TestClient) -> None:
    response = _post(client)
    assert response.status_code == 201

    body = response.json()
    assert body["brandName"] == "Test Brand"
    assert body["competitorCount"] == 1
    assert body["currentStage"] == 1
    assert body["status"] == "draft"
    # A new project is never pre-marked as demo data.
    assert body["isDemo"] is False


def test_create_project_requires_a_competitor(client: TestClient) -> None:
    response = _post(client, competitors=[])
    assert response.status_code == 422
    assert "competitors" in _error_fields(response)


def test_unknown_project_is_a_clean_404(client: TestClient) -> None:
    response = client.get("/api/v1/projects/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


# ------------------------------------------------------- free-text limits


def test_a_short_description_is_now_fine(client: TestClient) -> None:
    # The 40-character minimum is gone.
    assert _post(client, brandDescription="We sell coffee.").status_code == 201


def test_description_over_500_characters_is_rejected(client: TestClient) -> None:
    response = _post(client, brandDescription="x" * 501)
    assert response.status_code == 422
    # The field-level map is what lets the form attach the message to the input.
    assert "brandDescription" in _error_fields(response)


def test_description_is_still_required(client: TestClient) -> None:
    assert _post(client, brandDescription="   ").status_code == 422


def test_description_of_exactly_500_characters_is_accepted(client: TestClient) -> None:
    assert _post(client, brandDescription="x" * 500).status_code == 201


def test_target_audience_is_optional(client: TestClient) -> None:
    for missing in (None, "", "   "):
        response = _post(client, targetAudience=missing)
        assert response.status_code == 201, missing
        # Stored as null rather than an empty string.
        assert response.json()["targetAudience"] is None


def test_target_audience_over_120_characters_is_rejected(client: TestClient) -> None:
    response = _post(client, targetAudience="y" * 121)
    assert response.status_code == 422
    assert "targetAudience" in _error_fields(response)


# ------------------------------------------------------------ website tab


def test_website_comparison_requires_the_users_website(client: TestClient) -> None:
    for missing in (None, ""):
        response = _post(client, brandWebsite=missing)
        assert response.status_code == 422, missing
        assert "website" in _error_text(response)


def test_a_competitor_without_social_handles_is_fine(client: TestClient) -> None:
    # The intake form no longer collects Instagram/LinkedIn handles at all.
    project = _post(client).json()
    competitors = client.get(f"/api/v1/projects/{project['id']}/competitors").json()
    assert competitors[0]["socialHandles"] == []


# ------------------------------------------------------------- social tab


def _social(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "comparisonType": "social_media",
        "socialPlatform": "instagram",
        "brandName": "Verdant Roast Coffee",
        "brandWebsite": "https://www.instagram.com/verdantroast",
        "competitors": [
            {"name": "Northbrew", "landingPageUrl": "https://instagram.com/northbrew"}
        ],
    }
    payload.update(overrides)
    return payload


def test_valid_social_comparison_is_created(client: TestClient) -> None:
    response = _post(client, **_social())
    assert response.status_code == 201
    body = response.json()
    assert body["comparisonType"] == "social_media"
    assert body["socialPlatform"] == "instagram"
    assert body["ecommercePlatform"] is None


def test_social_comparison_requires_a_platform(client: TestClient) -> None:
    response = _post(client, **_social(socialPlatform=None))
    assert response.status_code == 422
    assert "platform" in _error_text(response)


def test_only_facebook_and_instagram_are_offered(client: TestClient) -> None:
    assert _post(client, **_social(socialPlatform="tiktok")).status_code == 422


def test_social_comparison_requires_the_users_page_link(client: TestClient) -> None:
    assert _post(client, **_social(brandWebsite="")).status_code == 422


@pytest.mark.parametrize(
    ("platform", "own", "competitor"),
    [
        ("instagram", "https://instagram.com/verdantroast", "https://www.instagram.com/northbrew/"),
        ("instagram", "https://www.instagram.com/verdantroast/", "https://m.instagram.com/northbrew"),
    ],
)
def test_links_on_the_chosen_platform_are_accepted(
    client: TestClient, platform: str, own: str, competitor: str
) -> None:
    payload = _social(
        socialPlatform=platform,
        brandWebsite=own,
        competitors=[{"name": "Northbrew", "landingPageUrl": competitor}],
    )
    assert _post(client, **payload).status_code == 201


def test_facebook_is_refused_until_it_has_a_scraper(client: TestClient) -> None:
    """The form disables it; the backend refuses it, so neither can be bypassed."""
    payload = _social(
        socialPlatform="facebook",
        brandWebsite="https://www.facebook.com/verdantroast",
        competitors=[{"name": "Northbrew", "landingPageUrl": "https://m.facebook.com/northbrew"}],
    )
    response = _post(client, **payload)
    assert response.status_code == 422
    assert "not available yet" in _error_text(response)
    assert "instagram" in _error_text(response)


@pytest.mark.parametrize(
    "wrong_link",
    [
        "https://www.facebook.com/verdantroast",     # the other platform
        "https://verdantroast.example",              # not a social site at all
        "https://instagram.com.evil.example/page",   # lookalike host
        "https://notinstagram.com/page",             # lookalike host
    ],
)
def test_own_link_off_the_chosen_platform_is_rejected(client: TestClient, wrong_link: str) -> None:
    response = _post(client, **_social(brandWebsite=wrong_link))
    assert response.status_code == 422
    assert "instagram" in _error_text(response)


def test_competitor_link_off_the_chosen_platform_is_rejected(client: TestClient) -> None:
    payload = _social(
        competitors=[{"name": "Northbrew", "landingPageUrl": "https://www.facebook.com/northbrew"}]
    )
    response = _post(client, **payload)
    assert response.status_code == 422
    assert "competitor 1" in _error_text(response)


def test_platform_choice_does_not_leak_onto_other_types(client: TestClient) -> None:
    # A stale choice from the form must not be stored on a website project.
    response = _post(client, socialPlatform="facebook", ecommercePlatform="daraz")
    assert response.status_code == 201
    body = response.json()
    assert body["socialPlatform"] is None
    assert body["ecommercePlatform"] is None


# ------------------------------------------------- long links (the bug)


def test_real_daraz_links_over_1000_characters_are_accepted(client: TestClient) -> None:
    """The reported bug: real links from Daraz search were rejected as too long."""
    assert len(DARAZ_DELL_MOUSE) > 1000 and len(DARAZ_HP_MOUSE) > 1000

    response = _post(
        client,
        comparisonType="ecommerce_product",
        ecommercePlatform="daraz",
        brandName="Dell wireless optical mouse",
        brandWebsite=DARAZ_DELL_MOUSE,
        competitors=[{"name": "HP W10", "landingPageUrl": DARAZ_HP_MOUSE}],
    )
    assert response.status_code == 201, response.json()

    project = response.json()
    # Stored exactly as pasted, not truncated or rewritten.
    assert project["brandWebsite"] == DARAZ_DELL_MOUSE

    competitors = client.get(f"/api/v1/projects/{project['id']}/competitors").json()
    assert competitors[0]["landingPageUrl"] == DARAZ_HP_MOUSE


@pytest.mark.parametrize("comparison", ["website", "social_media"])
def test_long_links_are_accepted_on_every_tab(client: TestClient, comparison: str) -> None:
    tracking = "?utm_source=search&clickTrackInfo=" + "a" * 1500
    if comparison == "website":
        payload = {
            "brandWebsite": f"https://testbrand.example/{tracking}",
            "competitors": [
                {"name": "Competitor One", "landingPageUrl": f"https://competitor.example/{tracking}"}
            ],
        }
    else:
        payload = _social(
            brandWebsite=f"https://www.instagram.com/verdantroast{tracking}",
            competitors=[
                {"name": "Northbrew", "landingPageUrl": f"https://instagram.com/northbrew{tracking}"}
            ],
        )
    assert _post(client, **payload).status_code == 201


def test_a_pathological_link_is_still_bounded(client: TestClient) -> None:
    # Longer than any web server will serve; the cap exists only for this.
    response = _post(client, brandWebsite="https://testbrand.example/?q=" + "a" * 9000)
    assert response.status_code == 422
