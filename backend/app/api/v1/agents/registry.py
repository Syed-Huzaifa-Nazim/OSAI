"""Agent selection.

One place decides which implementation each stage gets. Wiring in a real agent
is a one-line change here.
"""

from __future__ import annotations

from app.api.v1.agents.base import BaseAgent
from app.api.v1.agents.critic import MockCriticAgent
from app.api.v1.agents.insight import MockInsightAgent
from app.api.v1.agents.preprocess import MockPreprocessAgent
from app.api.v1.agents.scout import MockScoutAgent
from app.api.v1.agents.strategist import MockStrategistAgent
from app.core.config import settings

#: stage -> agent class. Swap a value for a live implementation when ready.
_MOCK_AGENTS: dict[int, type[BaseAgent]] = {
    2: MockScoutAgent,
    3: MockPreprocessAgent,
    4: MockInsightAgent,
    6: MockStrategistAgent,
}


def get_agent(stage: int) -> BaseAgent:
    """Returns the agent that owns ``stage``.

    Today every stage resolves to its mock. When live agents land, branch on
    ``settings.has_openai`` here: the callers do not change.
    """
    agent_class = _MOCK_AGENTS.get(stage)
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
