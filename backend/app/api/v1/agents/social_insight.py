"""Stage 4: Insight Agent for social comparisons (live for Instagram)."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.api.v1.agents.base import AgentResult, BaseAgent
from app.api.v1.agents.insight import MockInsightAgent

logger = logging.getLogger("optistratix.agents.insight.social")


class SocialInsightAgent(BaseAgent):
    name = "Insight Agent (social)"
    stage = 4
    is_live = True

    async def run(self, context: dict[str, Any]) -> AgentResult:
        project: dict[str, Any] = context.get("project") or {}
        if (project.get("social_platform") or "").lower() != "instagram":
            return await MockInsightAgent().run(context)

        from app.analysis.instagram import engine
        from app.analysis.instagram.llm import get_llm

        started = time.perf_counter()
        project_id: str = context["project_id"]
        posts = context.get("instagram_posts") or []
        comments = context.get("instagram_post_comments") or []

        gaps, warnings, summary = await asyncio.to_thread(
            engine.analyze_project, project_id, posts, comments, get_llm()
        )
        return AgentResult(
            payload=gaps,
            artifacts={"instagram_analysis": summary},
            items_processed=len(gaps),
            duration_ms=self._elapsed_ms(started),
            tokens_used=None,
            cost_usd=None,
            warnings=warnings,
        )