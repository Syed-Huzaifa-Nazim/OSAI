"""The service starts and reports what is wired up."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_reports_demo_mode(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    # The suite runs unconfigured, so demo mode must be on. If this flips,
    # tests would start writing to a real database.
    assert body["demoMode"] is True
    assert body["supabaseConfigured"] is False


def test_responses_carry_a_request_id(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.headers.get("X-Request-ID")
