"""Stage 4: Insight Agent (gap and opportunity analysis).

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
    name = "Insight Agent"
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
