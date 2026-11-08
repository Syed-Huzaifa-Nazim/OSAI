"""Stage 6b: Critic Agent (adversarial validation).

MOCK IMPLEMENTATION. Applies deterministic checks to the Strategist's draft and
records what it changed.

This is the agent the product's trust claim rests on, so the mock is written to
behave like the real thing in the way that matters: it produces a
``CriticFeedback`` record for every intervention, keeping both the original text
and the replacement. The UI renders those side by side. A live Critic must
preserve that contract: a critique that cannot be inspected is worth nothing.

A live implementation would prompt a second model to attack the draft on four
dimensions (strength, clarity, feasibility, evidence) and return structured
verdicts rather than prose.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from app.api.v1.agents.base import AgentResult, BaseAgent

logger = logging.getLogger("optistratix.agents.critic")

#: Above this many actions in one initiative, the plan is treated as unrealistic
#: for a small team and trimmed.
MAX_SUSTAINABLE_ACTIONS = 6

#: Claims that assert an outcome without naming a source.
UNSUPPORTED_MARKERS = (
    "will increase",
    "guarantees",
    "will double",
    "always works",
    "proven to",
)


def _feedback(
    *,
    verdict: str,
    dimension: str,
    comment: str,
    initiative_id: str | None = None,
    before: str | None = None,
    after: str | None = None,
    severity: str = "minor",
) -> dict[str, Any]:
    return {
        "id": f"crit_{uuid.uuid4().hex[:8]}",
        "target_initiative_id": initiative_id,
        "verdict": verdict,
        "dimension": dimension,
        "comment": comment,
        "before": before,
        "after": after,
        "severity": severity,
    }


class MockCriticAgent(BaseAgent):
    name = "Critic Agent"
    stage = 6
    is_live = False

    async def run(self, context: dict[str, Any]) -> AgentResult:
        started = time.perf_counter()
        draft: dict[str, Any] = context["draft"]
        has_budget: bool = context.get("has_budget", False)

        await asyncio.sleep(1.1)

        initiatives: list[dict[str, Any]] = list(draft.get("initiatives", []))
        feedback: list[dict[str, Any]] = []
        kept: list[dict[str, Any]] = []

        for initiative in initiatives:
            title = initiative.get("title", "")
            actions: list[str] = list(initiative.get("actions", []))

            # --- feasibility: a paid initiative with no declared budget ------
            requires_spend = any(
                marker in title.lower() for marker in ("paid", "ads", "retargeting")
            )
            if requires_spend and not has_budget:
                feedback.append(
                    _feedback(
                        verdict="rejected",
                        dimension="feasibility",
                        comment=(
                            "This initiative assumes a paid media budget, and nothing in the "
                            "intake indicates one exists. Removed as premature rather than left "
                            "in as an aspiration."
                        ),
                        before=title,
                        after=None,
                        severity="major",
                    )
                )
                continue

            # --- feasibility: an unsustainable number of actions -------------
            if len(actions) > MAX_SUSTAINABLE_ACTIONS:
                trimmed = actions[:MAX_SUSTAINABLE_ACTIONS]
                feedback.append(
                    _feedback(
                        verdict="challenged",
                        dimension="feasibility",
                        initiative_id=initiative["id"],
                        comment=(
                            f"The draft listed {len(actions)} steps for one initiative. A plan "
                            "nobody finishes is worse than a shorter one that gets done, so this "
                            f"was cut to {MAX_SUSTAINABLE_ACTIONS} with the rest deferred."
                        ),
                        before=f"{len(actions)} action steps",
                        after=f"{MAX_SUSTAINABLE_ACTIONS} action steps",
                        severity="major",
                    )
                )
                initiative = {**initiative, "actions": trimmed, "revised_from_draft": True}

            # --- evidence: an outcome asserted with no source ----------------
            impact = initiative.get("expected_impact", "")
            lowered = impact.lower()
            if any(marker in lowered for marker in UNSUPPORTED_MARKERS):
                hedged = (
                    impact.replace("will increase", "is expected to improve")
                    .replace("will double", "may meaningfully improve")
                    .replace("guarantees", "is intended to support")
                    .replace("proven to", "reported to")
                )
                feedback.append(
                    _feedback(
                        verdict="strengthened",
                        dimension="evidence",
                        initiative_id=initiative["id"],
                        comment=(
                            "The draft asserted an outcome it could not support from the "
                            "retrieved sources. Reworded so the claim matches the evidence "
                            "actually available."
                        ),
                        before=impact,
                        after=hedged,
                        severity="minor",
                    )
                )
                initiative = {
                    **initiative,
                    "expected_impact": hedged,
                    "revised_from_draft": True,
                }

            # --- clarity: an initiative with no measurable step ---------------
            if actions and not any(
                word in " ".join(actions).lower()
                for word in ("measure", "track", "review", "report", "test")
            ):
                measurement = "Define how this will be measured, and review at week 8."
                extended = [*initiative.get("actions", []), measurement]
                # Measurement is mandatory, so if adding it breaches the
                # feasibility cap, the last optional step gives way instead.
                if len(extended) > MAX_SUSTAINABLE_ACTIONS:
                    extended = [*extended[: MAX_SUSTAINABLE_ACTIONS - 1], measurement]
                feedback.append(
                    _feedback(
                        verdict="strengthened",
                        dimension="clarity",
                        initiative_id=initiative["id"],
                        comment=(
                            "No step in this initiative described how success would be judged, "
                            "which makes it impossible to tell later whether it worked. Added an "
                            "explicit measurement step."
                        ),
                        before="No measurement step",
                        after=measurement,
                        severity="minor",
                    )
                )
                initiative = {**initiative, "actions": extended, "revised_from_draft": True}

            kept.append(initiative)

        # An initiative the Critic left alone is still a judgement worth recording.
        for initiative in kept:
            if not initiative.get("revised_from_draft"):
                feedback.append(
                    _feedback(
                        verdict="approved",
                        dimension="strength",
                        initiative_id=initiative["id"],
                        comment=(
                            "Well-evidenced and correctly sized. No change needed."
                        ),
                        severity="info",
                    )
                )

        logger.info(
            "Critic (mock): %d initiatives in, %d out, %d interventions",
            len(initiatives),
            len(kept),
            len(feedback),
        )

        return AgentResult(
            payload={"initiatives": kept, "critic_feedback": feedback},
            items_processed=len(feedback),
            duration_ms=self._elapsed_ms(started),
            tokens_used=13_200,
            cost_usd=0.198,
            warnings=["Mock Critic: rule-based checks, not a second model."],
        )
