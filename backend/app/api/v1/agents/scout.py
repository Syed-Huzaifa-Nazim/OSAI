"""Stage 2: Scout Agent (data acquisition).

MOCK IMPLEMENTATION. Returns the hand-written source set from
``app.services.demo_data`` instead of scraping anything.

A live implementation would:
  1. Fetch each competitor's landing page and extract readable text.
  2. Pull recent posts for each declared social handle.
  3. Search review sites, forums and news for brand and competitor mentions.
  4. Return a ScrapedSource per artefact, with the raw text attached.

The return shape is what stage 3 consumes, so a real Scout is a drop-in swap.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.api.v1.agents.base import AgentResult, BaseAgent
from app.services import demo_data

logger = logging.getLogger("optistratix.agents.scout")


class MockScoutAgent(BaseAgent):
    name = "Scout Agent"
    stage = 2
    is_live = False

    async def run(self, context: dict[str, Any]) -> AgentResult:
        started = time.perf_counter()
        project_id: str = context["project_id"]
        competitors: list[dict[str, Any]] = context.get("competitors", [])

        logger.info(
            "Scout (mock) collecting for project=%s competitors=%d", project_id, len(competitors)
        )
        # Stands in for network latency so the stepper has something to animate.
        await asyncio.sleep(1.2)

        sources = demo_data.build_sources(project_id, competitors)

        return AgentResult(
            payload=sources,
            items_processed=len(sources),
            duration_ms=self._elapsed_ms(started),
            tokens_used=42_100,
            cost_usd=0.421,
            warnings=["Mock Scout: no network requests were made."],
        )
