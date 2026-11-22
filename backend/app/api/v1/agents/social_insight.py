"""Stage 4: Gap Engine for social comparisons.

LIVE for Instagram. The gaps come from app/analysis/instagram/: a trained
Random Forest grades each account's engagement, TreeSHAP explains the grades,
and statistical tests against similar accounts cover formats, hashtags, weak spots,
picture quality and the profile checklist. Every gap cites real scraped posts as evidence.

Any other social platform returns no gaps and says it is not built yet (never the
hand-written demo gaps).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.api.v1.agents.base import AgentResult, BaseAgent
from app.api.v1.agents.insight import NotBuiltInsightAgent

logger = logging.getLogger("optistratix.agents.insight.social")


class SocialInsightAgent(BaseAgent):
    name = "Gap Engine (social)"
    stage = 4
    is_live = True

    async def run(self, context: dict[str, Any]) -> AgentResult:
        project: dict[str, Any] = context.get("project") or {}
        platform = (project.get("social_platform") or "").lower()
        if platform != "instagram":
            self.not_built = True          # the pipeline then reports the "not built yet" message as the stage result
            return await NotBuiltInsightAgent(f"{platform.capitalize() or 'this platform'} accounts").run(context)

        # Imported here so the rest of the API starts even before the analysis
        # libraries (scikit-learn, shap) are installed.
        from app.analysis.instagram import engine
        from app.analysis.instagram.llm import get_llm

        started = time.perf_counter()
        project_id: str = context["project_id"]
        posts = context.get("instagram_posts") or []
        comments = context.get("instagram_post_comments") or []
        logger.info("Instagram analysis project=%s posts=%d comments=%d",
                    project_id, len(posts), len(comments))

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


__all__ = ["SocialInsightAgent"]
