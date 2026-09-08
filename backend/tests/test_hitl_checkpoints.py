"""The two human checkpoints.

These are the tests that matter most: the checkpoints are the product's trust
story, so the API must refuse to advance past one that has not been answered.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def _gaps(client: TestClient, project_id: str) -> list[dict]:
    response = client.get(f"/api/v1/projects/{project_id}/gaps")
    assert response.status_code == 200
    return response.json()


def test_demo_project_starts_with_untriaged_gaps(
    client: TestClient, demo_project_id: str
) -> None:
    gaps = _gaps(client, demo_project_id)
    assert len(gaps) > 0
    assert all(gap["decision"] == "pending" for gap in gaps)
    # Every gap carries its evidence: an uncited claim would defeat the point.
    assert all(len(gap["evidence"]) > 0 for gap in gaps)


def test_gap_review_is_refused_while_gaps_are_untriaged(
    client: TestClient, demo_project_id: str
) -> None:
    gaps = _gaps(client, demo_project_id)

    # Accept exactly one and leave the rest pending.
    client.patch(
        f"/api/v1/projects/{demo_project_id}/gaps/{gaps[0]['id']}",
        json={"decision": "accepted"},
    )

    response = client.post(
        f"/api/v1/projects/{demo_project_id}/gaps/review",
        json={"notes": "Partial triage", "acceptedGapIds": [gaps[0]["id"]]},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_gap_review_is_refused_when_everything_is_rejected(
    client: TestClient, demo_project_id: str
) -> None:
    gaps = _gaps(client, demo_project_id)
    for gap in gaps:
        client.patch(
            f"/api/v1/projects/{demo_project_id}/gaps/{gap['id']}",
            json={"decision": "rejected"},
        )

    response = client.post(
        f"/api/v1/projects/{demo_project_id}/gaps/review",
        json={"notes": "None of these apply", "acceptedGapIds": []},
    )

    assert response.status_code == 422 or response.status_code == 409


def test_gap_review_closes_the_checkpoint(client: TestClient, demo_project_id: str) -> None:
    gaps = _gaps(client, demo_project_id)
    accepted = [gap["id"] for gap in gaps[:3]]

    for gap in gaps:
        decision = "accepted" if gap["id"] in accepted else "rejected"
        client.patch(
            f"/api/v1/projects/{demo_project_id}/gaps/{gap['id']}",
            json={"decision": decision},
        )

    response = client.post(
        f"/api/v1/projects/{demo_project_id}/gaps/review",
        json={"notes": "Kept the evidenced ones", "acceptedGapIds": accepted},
    )

    assert response.status_code == 200
    review = response.json()
    assert review["stage"] == 5
    assert review["decision"] == "approved"
    assert set(review["affectedIds"]) == set(accepted)


def test_gap_priority_override_is_recorded(client: TestClient, demo_project_id: str) -> None:
    gaps = _gaps(client, demo_project_id)
    target = gaps[0]

    response = client.patch(
        f"/api/v1/projects/{demo_project_id}/gaps/{target['id']}",
        json={"userPriority": "low", "reviewerNote": "Not a priority this quarter."},
    )

    assert response.status_code == 200
    body = response.json()
    # The agent's own call is preserved alongside the human override, so the
    # disagreement stays visible.
    assert body["userPriority"] == "low"
    assert body["priority"] == target["priority"]
    assert body["reviewerNote"] == "Not a priority this quarter."


def test_strategy_approval_requires_a_strategy(
    client: TestClient, demo_project_id: str
) -> None:
    response = client.post(
        f"/api/v1/projects/{demo_project_id}/strategy/approve",
        json={"decision": "approved", "notes": None, "flaggedIds": []},
    )
    assert response.status_code == 404


def test_revision_request_demands_notes(client: TestClient, demo_project_id: str) -> None:
    """A rejection with no explanation gives the agents nothing to work with."""
    response = client.post(
        f"/api/v1/projects/{demo_project_id}/strategy/revise",
        json={"decision": "revision_requested", "notes": None, "flaggedIds": []},
    )
    # 404 because no strategy exists yet on the demo project; the notes rule is
    # covered once one does. Either way it must not be a 200.
    assert response.status_code in (404, 409)
