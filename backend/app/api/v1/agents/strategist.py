"""Stage 6a: Strategist Agent (strategy generation).

MOCK IMPLEMENTATION. Builds a strategy from the gaps the human accepted at
HITL #1, using hand-written initiative templates.

A live implementation would prompt the model with the accepted gaps, their
evidence, the brand intake and the reviewer's notes, and require every
initiative to name the gap it addresses.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.api.v1.agents.base import AgentResult, BaseAgent
from app.services import demo_data

logger = logging.getLogger("optistratix.agents.strategist")


class MockStrategistAgent(BaseAgent):
    name = "Strategist Agent"
    stage = 6
    is_live = False

    async def run(self, context: dict[str, Any]) -> AgentResult:
        started = time.perf_counter()
        project_id: str = context["project_id"]
        accepted_gaps: list[dict[str, Any]] = context.get("accepted_gaps", [])
        project: dict[str, Any] = context.get("project", {})

        logger.info(
            "Strategist (mock) drafting for project=%s accepted_gaps=%d",
            project_id,
            len(accepted_gaps),
        )
        await asyncio.sleep(1.4)

        draft = demo_data.build_strategy_draft(project_id, project, accepted_gaps)

        return AgentResult(
            payload=draft,
            items_processed=len(draft["initiatives"]),
            duration_ms=self._elapsed_ms(started),
            tokens_used=21_400,
            cost_usd=0.321,
            warnings=["Mock Strategist: initiatives are templated, not model-generated."],
        )
