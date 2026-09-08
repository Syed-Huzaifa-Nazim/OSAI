"""Project creation and the stage-1 intake contract."""

from __future__ import annotations

from fastapi.testclient import TestClient

VALID_PROJECT = {
    "brandName": "Test Brand",
    "brandWebsite": "https://testbrand.example",
    "brandDescription": (
        "A test brand with a description long enough to satisfy the minimum length rule "
        "that the intake form enforces."
    ),
    "industry": "saas",
    "targetAudience": "Small teams evaluating analytics tooling for the first time.",
    "objectives": ["Grow trial signups"],
    "competitors": [
        {
            "name": "Competitor One",
            "landingPageUrl": "https://competitor-one.example",
            "socialHandles": [{"platform": "instagram", "handle": "@compone"}],
            "notes": None,
        }
    ],
}


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
    response = client.post("/api/v1/projects", json=VALID_PROJECT)
    assert response.status_code == 201

    body = response.json()
    assert body["brandName"] == "Test Brand"
    assert body["competitorCount"] == 1
    assert body["currentStage"] == 1
    assert body["status"] == "draft"
    # A new project is never pre-marked as demo data.
    assert body["isDemo"] is False


def test_create_project_rejects_short_description(client: TestClient) -> None:
    payload = {**VALID_PROJECT, "brandDescription": "Too short"}
    response = client.post("/api/v1/projects", json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    # The field-level map is what lets the form attach the message to the input.
    assert "brandDescription" in error["fields"]


def test_create_project_requires_a_competitor(client: TestClient) -> None:
    payload = {**VALID_PROJECT, "competitors": []}
    response = client.post("/api/v1/projects", json=payload)

    assert response.status_code == 422
    assert "competitors" in response.json()["error"]["fields"]


def test_unknown_project_is_a_clean_404(client: TestClient) -> None:
    response = client.get("/api/v1/projects/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
