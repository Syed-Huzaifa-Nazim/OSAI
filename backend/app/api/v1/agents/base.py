"""The contract every agent implements."""

from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    """What an agent hands back to the pipeline runner.

    ``tokens_used`` and ``cost_usd`` are None for agents that make no LLM calls,
    which is how the UI knows to render a dash rather than a zero.
    """

    payload: Any
    items_processed: int = 0
    duration_ms: int = 0
    tokens_used: int | None = None
    cost_usd: float | None = None
    warnings: list[str] = field(default_factory=list)
    #: Secondary output the runner persists alongside ``payload``, keyed by
    #: what it is. A stage whose agent produces more than one kind of record
    #: uses this rather than overloading ``payload``, which keeps the runner
    #: the only place that knows how anything is stored. Stage 2 puts scraped
    #: ``ecommerce_products`` here; the website and social paths leave it empty.
    artifacts: dict[str, Any] = field(default_factory=dict)


class BaseAgent(abc.ABC):
    """A pipeline agent.

    Implementations must be side-effect free with respect to the database: the
    runner persists whatever comes back. That keeps a real agent swappable for
    a mock without either of them knowing how storage works.
    """

    #: Human-readable, used in logs and stage messages.
    name: str = "agent"
    #: Which pipeline stage this agent owns.
    stage: int = 0
    #: False for the mock implementations shipped in this repo.
    is_live: bool = False

    @abc.abstractmethod
    async def run(self, context: dict[str, Any]) -> AgentResult:
        """Executes the agent's stage against ``context``."""

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return int((time.perf_counter() - started) * 1000)
