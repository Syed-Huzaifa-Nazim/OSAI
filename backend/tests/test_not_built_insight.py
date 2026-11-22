"""Sources without a gap analysis of their own get no gaps and a plain message, never the demo gaps."""

from __future__ import annotations

import asyncio

from app.api.v1.agents.insight import MockInsightAgent, NotBuiltInsightAgent
from app.api.v1.agents.registry import get_agent
from app.api.v1.agents.social_insight import SocialInsightAgent


def test_a_real_website_project_gets_no_demo_gaps():
    agent = get_agent(4, {"comparison_type": "website", "is_demo": False})
    assert isinstance(agent, NotBuiltInsightAgent)
    result = asyncio.run(agent.run({"project_id": "p1"}))
    assert result.payload == [] and "not built yet" in result.warnings[0]


def test_the_seeded_demo_project_keeps_its_demo_gaps():
    assert isinstance(get_agent(4, {"comparison_type": "website", "is_demo": True}), MockInsightAgent)


def test_a_facebook_project_gets_no_demo_gaps():
    agent = SocialInsightAgent()
    result = asyncio.run(agent.run({"project_id": "p1", "project": {"social_platform": "facebook"}}))
    assert result.payload == [] and "Facebook" in result.warnings[0] and agent.not_built
