"""The Critic.

The Critic is the evidence behind "reduces hallucinated insights", so what is
tested here is not that it runs, but that its output stays inspectable: every
intervention keeps both the original text and the replacement.
"""

from __future__ import annotations

import asyncio

from app.api.v1.agents.critic import MockCriticAgent


def _draft() -> dict:
    return {
        "initiatives": [
            {
                "id": "init-paid",
                "title": "Launch a paid retargeting programme",
                "rationale": "Retarget non-converting visitors.",
                "actions": ["Set a $4,000 monthly budget."],
                "channel": "Paid social",
                "effort": "high",
                "expected_impact": "Paid retargeting will increase conversion.",
                "timeline_weeks": 6,
                "linked_gap_ids": [],
                "revised_from_draft": False,
            },
            {
                "id": "init-content",
                "title": "Publish a weekly guide series",
                "rationale": "Enter the informational query cluster.",
                "actions": [f"Step {index}" for index in range(1, 10)],
                "channel": "Organic search",
                "effort": "high",
                "expected_impact": "Organic traffic is expected to improve. Review at week 8.",
                "timeline_weeks": 12,
                "linked_gap_ids": ["gap-1"],
                "revised_from_draft": False,
            },
        ]
    }


def test_critic_rejects_paid_work_with_no_budget() -> None:
    result = asyncio.run(MockCriticAgent().run({"draft": _draft(), "has_budget": False}))

    kept = result.payload["initiatives"]
    feedback = result.payload["critic_feedback"]

    assert not any(item["id"] == "init-paid" for item in kept)

    rejection = next(item for item in feedback if item["verdict"] == "rejected")
    assert rejection["dimension"] == "feasibility"
    assert rejection["severity"] == "major"
    # The removed text is retained so the UI can show what was dropped.
    assert rejection["before"]
    assert rejection["after"] is None


def test_critic_keeps_paid_work_when_a_budget_exists() -> None:
    result = asyncio.run(MockCriticAgent().run({"draft": _draft(), "has_budget": True}))
    kept = result.payload["initiatives"]
    assert any(item["id"] == "init-paid" for item in kept)


def test_critic_trims_an_unsustainable_plan() -> None:
    result = asyncio.run(MockCriticAgent().run({"draft": _draft(), "has_budget": False}))

    content = next(
        item for item in result.payload["initiatives"] if item["id"] == "init-content"
    )
    assert len(content["actions"]) <= 6
    assert content["revised_from_draft"] is True

    challenge = next(
        item
        for item in result.payload["critic_feedback"]
        if item["verdict"] == "challenged" and item["dimension"] == "feasibility"
    )
    assert challenge["before"] != challenge["after"]


def test_every_intervention_is_inspectable() -> None:
    """A critique nobody can inspect is worth nothing, so every record must
    carry the fields the transparency panel renders."""
    result = asyncio.run(MockCriticAgent().run({"draft": _draft(), "has_budget": False}))

    for item in result.payload["critic_feedback"]:
        assert item["id"]
        assert item["verdict"] in {"strengthened", "challenged", "rejected", "approved"}
        assert item["dimension"] in {"strength", "clarity", "feasibility", "evidence"}
        assert item["comment"]
        assert item["severity"] in {"info", "minor", "major"}
        # Anything that changed the draft must show what it changed.
        if item["verdict"] in {"challenged", "strengthened"}:
            assert item["before"] is not None
