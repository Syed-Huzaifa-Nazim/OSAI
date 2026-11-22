"""Stage 4: Gap Engine (gap and opportunity analysis).

MOCK IMPLEMENTATION. Returns the hand-written gap set from
``app.services.demo_data``, with evidence pointing at the project's real
source rows so the citation trail in the UI resolves correctly.

A live implementation would, for each analysis dimension:
  1. Retrieve the most relevant chunks from the project's Chroma collection.
  2. Ask the model to compare the brand against them and name a specific gap.
  3. Require the model to quote the passage supporting each claim.
  4. Reject any gap whose quote cannot be matched back to a retrieved chunk. The check that keeps the evidence trail honest.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.api.v1.agents.base import AgentResult, BaseAgent
from app.services import demo_data

logger = logging.getLogger("optistratix.agents.insight")


class MockInsightAgent(BaseAgent):
    name = "Gap Engine"
    stage = 4
    is_live = False

    async def run(self, context: dict[str, Any]) -> AgentResult:
        started = time.perf_counter()
        project_id: str = context["project_id"]
        sources: list[dict[str, Any]] = context.get("sources", [])

        logger.info("Insight (mock) analysing project=%s sources=%d", project_id, len(sources))
        await asyncio.sleep(1.0)

        gaps = demo_data.build_gaps(project_id, sources)

        return AgentResult(
            payload=gaps,
            items_processed=len(gaps),
            duration_ms=self._elapsed_ms(started),
            tokens_used=38_900,
            cost_usd=0.583,
            warnings=["Mock Insight: gaps are hand-written, not model-generated."],
        )


class NotBuiltInsightAgent(BaseAgent):
    """Stage 4 for sources whose gap analysis is not built yet (websites, social platforms other than Instagram).

    It returns NO gaps and says so, instead of the hand-written demo gaps: a seller must never see template
    findings presented as an analysis of their own account. The seeded demo project keeps the mock.
    """

    name = "Gap Engine (not built yet)"
    stage = 4
    is_live = False
    not_built = True

    def __init__(self, what: str = "this source") -> None:
        self.what = what

    async def run(self, context: dict[str, Any]) -> AgentResult:
        logger.info("Insight not built for %s (project=%s)", self.what, context.get("project_id"))
        return AgentResult(
            payload=[],
            items_processed=0,
            duration_ms=0,
            tokens_used=None,
            cost_usd=None,
            warnings=[f"Gap analysis for {self.what} is not built yet, so no gaps are shown."],
        )
