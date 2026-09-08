"""Agent service modules (Scout, Insight, Strategist, Critic).

Every agent is a swappable module behind ``BaseAgent``. The implementations
shipped here are MOCKS that return realistic, hand-written data so the whole
nine-stage pipeline is demoable before any LLM is wired in. Replacing one with a
real LangChain/CrewAI agent means implementing the same ``run`` signature and
changing the line in ``get_agent``. Nothing else in the codebase moves.
"""

from app.api.v1.agents.base import AgentResult, BaseAgent  # noqa: F401
from app.api.v1.agents.registry import get_agent  # noqa: F401
