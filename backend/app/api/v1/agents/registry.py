"""Agent selection.

One place decides which implementation each stage gets. Wiring in a real agent
is a one-line change here.
"""

from __future__ import annotations

from typing import Any

from app.api.v1.agents.base import BaseAgent
from app.api.v1.agents.critic import MockCriticAgent
from app.api.v1.agents.ecommerce_insight import EcommerceInsightAgent
from app.api.v1.agents.ecommerce_preprocess import EcommercePreprocessAgent
from app.api.v1.agents.ecommerce_scout import EcommerceScoutAgent
from app.api.v1.agents.insight import MockInsightAgent
from app.api.v1.agents.preprocess import MockPreprocessAgent
from app.api.v1.agents.scout import MockScoutAgent
from app.api.v1.agents.social_insight import SocialInsightAgent
from app.api.v1.agents.source_preprocess import SourcePreprocessAgent
from app.api.v1.agents.source_scout import SocialScoutAgent, WebsiteScoutAgent
from app.api.v1.agents.strategist import MockStrategistAgent
from app.core.config import settings
from app.models.project import ComparisonType

#: stage -> agent class. Swap a value for a live implementation when ready.
_MOCK_AGENTS: dict[int, type[BaseAgent]] = {
    2: MockScoutAgent,
    3: MockPreprocessAgent,
    4: MockInsightAgent,
    6: MockStrategistAgent,
}

#: Stages that behave differently for an e-commerce comparison, because the
#: input is a structured product listing rather than a page of prose. Every
#: other stage is shared: the same Strategist, Critic, checkpoints and document
#: run regardless of what was scraped.
_ECOMMERCE_AGENTS: dict[int, type[BaseAgent]] = {
    2: EcommerceScoutAgent,
    3: EcommercePreprocessAgent,
    4: EcommerceInsightAgent,
}

#: The website and social comparisons scrape for real too, through their own
#: scrapers. Only stages 2 and 3 differ: what changes is where the text comes
#: from, not what happens to it afterwards.
_WEBSITE_AGENTS: dict[int, type[BaseAgent]] = {
    2: WebsiteScoutAgent,
    3: SourcePreprocessAgent,
}

_SOCIAL_AGENTS: dict[int, type[BaseAgent]] = {
    2: SocialScoutAgent,
    3: SourcePreprocessAgent,
    4: SocialInsightAgent,
}

#: comparison type -> the agents that replace the defaults for it.
_BY_COMPARISON_TYPE: dict[str, dict[int, type[BaseAgent]]] = {
    ComparisonType.ECOMMERCE_PRODUCT.value: _ECOMMERCE_AGENTS,
    ComparisonType.WEBSITE.value: _WEBSITE_AGENTS,
    ComparisonType.SOCIAL_MEDIA.value: _SOCIAL_AGENTS,
}


def get_agent(stage: int, project: dict[str, Any] | None = None) -> BaseAgent:
    """Returns the agent that owns ``stage`` for this project.

    ``project`` selects the data-acquisition strategy: each comparison type
    gets its own scraper-backed agents for the stages that read and store
    source material, and falls back to the shared defaults for the rest.
    Passing nothing keeps the original behaviour, so existing callers and tests
    are unaffected.

    The seeded demo project is the one exception: it is a website comparison
    whose links do not resolve, and it exists to walk the nine stages with no
    network, so it keeps the mock agents.

    When live LLM agents land, branch on ``settings.has_openai`` here: the
    callers still do not change.
    """
    overrides: dict[int, type[BaseAgent]] = {}
    if project and not project.get("is_demo"):
        overrides = _BY_COMPARISON_TYPE.get(project.get("comparison_type") or "", {})

    agent_class = overrides.get(stage) or _MOCK_AGENTS.get(stage)
    if agent_class is None:
        raise ValueError(f"No agent is registered for stage {stage}")
    return agent_class()


def get_critic() -> BaseAgent:
    """The Critic runs inside stage 6, after the Strategist, rather than owning
    a stage of its own."""
    return MockCriticAgent()


def agents_are_live() -> bool:
    """True once real LLM-backed agents are wired in. Drives the 'demo data'
    badging in the UI."""
    return settings.has_openai and not settings.is_demo
