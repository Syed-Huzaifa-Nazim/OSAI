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


def get_agent(stage: int, project: dict[str, Any] | None = None) -> BaseAgent:
    """Returns the agent that owns ``stage`` for this project.

    ``project`` selects the data-acquisition strategy: an e-commerce comparison
    gets the scraper-backed agents for stages 2-4, everything else gets the
    defaults. Passing nothing keeps the original behaviour, so existing callers
    and tests are unaffected.

    When live LLM agents land, branch on ``settings.has_openai`` here: the
    callers still do not change.
    """
    if project and _is_ecommerce(project):
        agent_class = _ECOMMERCE_AGENTS.get(stage) or _MOCK_AGENTS.get(stage)
    else:
        agent_class = _MOCK_AGENTS.get(stage)

    if agent_class is None:
        raise ValueError(f"No agent is registered for stage {stage}")
    return agent_class()


def _is_ecommerce(project: dict[str, Any]) -> bool:
    return project.get("comparison_type") == ComparisonType.ECOMMERCE_PRODUCT.value


def get_critic() -> BaseAgent:
    """The Critic runs inside stage 6, after the Strategist, rather than owning
    a stage of its own."""
    return MockCriticAgent()


def agents_are_live() -> bool:
    """True once real LLM-backed agents are wired in. Drives the 'demo data'
    badging in the UI."""
    return settings.has_openai and not settings.is_demo
