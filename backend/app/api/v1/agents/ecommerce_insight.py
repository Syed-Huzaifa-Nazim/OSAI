"""Stage 4: gap analysis for e-commerce comparisons.

LIVE IMPLEMENTATION, and not an LLM one. Every gap it produces is arithmetic
over two scraped listings.

The scraper's comparison engine (``app/scrapers/daraz/metrics.py``) groups ~50
metadata fields into eight parameters and decides, per field, which listing
wins. A group the competitor leads on is a gap; the metric rows behind it are
the justification. So a claim like "your listing is under-specified" arrives
already attached to the two numbers that make it true, rather than needing a
model to be talked out of inventing them.

Supporting quotes come from the competitor's own chunks in the project's
Chroma collection, scoped to the field types that parameter cares about.
Metadata-only groups (pricing, variants) have no prose to quote, so their
evidence is the measurement itself.

The output is ordinary ``Gap`` rows, so HITL checkpoint #1, the Strategist and
the Critic all work on e-commerce projects with no changes.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.api.v1.agents.base import AgentResult, BaseAgent
from app.scrapers import COMPETITOR, OWN, get_scraper
from app.services import demo_data
from app.services.repository import new_id
from app.vectorstore import chroma

logger = logging.getLogger("optistratix.agents.insight.ecommerce")

#: Quotes pulled per parameter group, per competitor.
EVIDENCE_PER_GROUP = 3


class EcommerceInsightAgent(BaseAgent):
    name = "Insight Agent (e-commerce)"
    stage = 4
    is_live = True

    async def run(self, context: dict[str, Any]) -> AgentResult:
        started = time.perf_counter()
        project_id: str = context["project_id"]
        project: dict[str, Any] = context.get("project") or {}
        products: list[dict[str, Any]] = context.get("ecommerce_products", [])

        own = next((p for p in products if p.get("role") == OWN), None)
        competitors = [p for p in products if p.get("role") == COMPETITOR]

        if own is None or not competitors:
            return AgentResult(
                payload=[],
                items_processed=0,
                duration_ms=self._elapsed_ms(started),
                warnings=["Need both your listing and at least one competitor's to compare."],
            )

        scraper = get_scraper(project.get("ecommerce_platform") or own.get("platform"))
        own_meta = own.get("raw_metadata") or {}

        gaps: list[dict[str, Any]] = []
        comparisons: list[dict[str, Any]] = []
        warnings: list[str] = []

        for competitor in competitors:
            competitor_meta = competitor.get("raw_metadata") or {}
            groups = scraper.build_metrics(own_meta, competitor_meta)

            comparisons.append({
                "competitor_product_id": competitor["id"],
                "competitor_name": competitor.get("product_name"),
                "groups": groups,
            })

            for group in groups:
                if group["competitor_wins"] <= 0:
                    # Nothing to fix in this group against this competitor.
                    continue
                gaps.append(
                    self._gap_from_group(
                        project_id=project_id,
                        group=group,
                        own=own,
                        competitor=competitor,
                    )
                )

        gaps = self._deduplicate(gaps)

        if not gaps:
            warnings.append(
                "Your listing matches or beats every competitor on all measured metrics, "
                "so no gaps were raised."
            )

        logger.info(
            "Insight (e-commerce) found %d gaps for %s across %d competitors",
            len(gaps), project_id, len(competitors),
        )

        return AgentResult(
            payload=gaps,
            artifacts={"ecommerce_comparisons": comparisons},
            items_processed=len(gaps),
            duration_ms=self._elapsed_ms(started),
            # Rule-based comparison: no model was called.
            tokens_used=None,
            cost_usd=None,
            warnings=warnings,
        )

    # ------------------------------------------------------------ gap building

    def _gap_from_group(
        self,
        *,
        project_id: str,
        group: dict[str, Any],
        own: dict[str, Any],
        competitor: dict[str, Any],
    ) -> dict[str, Any]:
        losing = [row for row in group["metrics"] if row["winner"] == COMPETITOR]
        measured = [row for row in group["metrics"] if row["winner"] is not None]

        return {
            "id": new_id("gap"),
            "project_id": project_id,
            "title": self._title(group, losing, competitor),
            "description": self._description(group, losing),
            "category": group["gap_category"],
            "priority": self._priority(group, measured),
            "user_priority": None,
            "confidence": self._confidence(group, measured),
            "evidence": self._evidence(project_id, group, losing, competitor),
            "opportunity": self._opportunity(group, losing),
            "decision": "pending",
            "reviewer_note": None,
            "created_at": demo_data.iso(),
        }

    @staticmethod
    def _title(group: dict[str, Any], losing: list[dict[str, Any]], competitor: dict[str, Any]) -> str:
        headline = losing[0]["label"].lower() if losing else group["label"].lower()
        name = (competitor.get("product_name") or "the competitor")[:60]
        return f"{group['label']}: {name} leads on {headline}"

    @staticmethod
    def _description(group: dict[str, Any], losing: list[dict[str, Any]]) -> str:
        """The rule-based findings, followed by the rows that produced them."""
        lines = list(group["insights"])
        for row in losing[:5]:
            own_value = _format(row["own"], row["unit"])
            competitor_value = _format(row["competitor"], row["unit"])
            detail = f"{row['label']}: you {own_value} vs competitor {competitor_value}"
            if row["delta_label"]:
                detail += f" ({row['delta_label'].lower()})"
            lines.append(detail + ".")
        return "\n".join(lines)

    @staticmethod
    def _priority(group: dict[str, Any], measured: list[dict[str, Any]]) -> str:
        """How much of the group is lost, not how many rows.

        Losing 3 of 4 measurable metrics is a bigger problem than losing 3 of
        12, so the share is what drives priority.
        """
        losses = group["competitor_wins"]
        share = losses / len(measured) if measured else 0.0
        if share >= 0.75 and losses >= 3:
            return "critical"
        if share >= 0.5:
            return "high"
        if share >= 0.25:
            return "medium"
        return "low"

    @staticmethod
    def _confidence(group: dict[str, Any], measured: list[dict[str, Any]]) -> float:
        """How much of the group could actually be measured.

        A field the scraper could not extract has no winner, so a group where
        most fields came back empty yields a low-confidence gap rather than a
        confident claim built on two data points.
        """
        total = len(group["metrics"])
        if not total:
            return 0.0
        coverage = len(measured) / total
        return round(min(0.99, 0.55 + coverage * 0.4), 2)

    @staticmethod
    def _opportunity(group: dict[str, Any], losing: list[dict[str, Any]]) -> str:
        fields = ", ".join(row["label"].lower() for row in losing[:3])
        return (
            f"Close the {group['label'].lower()} gap by improving {fields}. "
            "Each of these is a listing change you control directly."
        )

    # --------------------------------------------------------------- evidence

    def _evidence(
        self,
        project_id: str,
        group: dict[str, Any],
        losing: list[dict[str, Any]],
        competitor: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Quotes from the competitor's listing that show the gap.

        Falls back to quoting the measurement when a group has no prose behind
        it, or when the vector store is unavailable, so a gap is never left
        without a citation.
        """
        source_id = competitor.get("source_id") or ""
        source_url = competitor.get("url", "")
        source_title = competitor.get("product_name", "")

        field_types = group.get("semantic_field_types") or []
        query = group.get("query")

        evidence: list[dict[str, Any]] = []
        if field_types and query:
            where: dict[str, Any] = {
                "$and": [
                    {"product_id": {"$eq": competitor["id"]}},
                    (
                        {"field_type": {"$eq": field_types[0]}}
                        if len(field_types) == 1
                        else {"field_type": {"$in": list(field_types)}}
                    ),
                ]
            }
            try:
                hits = chroma.query(project_id, query, n_results=EVIDENCE_PER_GROUP, where=where)
            except Exception as exc:  # noqa: BLE001 - fall through to the metric quote
                logger.warning("Evidence retrieval failed for %s: %s", project_id, exc)
                hits = []

            for hit in hits:
                metadata = hit.get("metadata") or {}
                evidence.append({
                    "source_id": metadata.get("source_id") or source_id,
                    "source_url": metadata.get("source_url") or source_url,
                    "source_title": metadata.get("source_title") or source_title,
                    "quote": (hit.get("document") or "")[:600],
                    "relevance": round(float(hit.get("relevance") or 0.0), 4),
                })

        if not evidence:
            for row in losing[:EVIDENCE_PER_GROUP]:
                evidence.append({
                    "source_id": source_id,
                    "source_url": source_url,
                    "source_title": source_title,
                    # A measured field, quoted as the measurement. Relevance is
                    # 1.0 because this is the extracted value itself, not a
                    # retrieved approximation of it.
                    "quote": (
                        f"{row['label']}: {_format(row['competitor'], row['unit'])} "
                        f"(yours: {_format(row['own'], row['unit'])})"
                    ),
                    "relevance": 1.0,
                })

        return evidence

    # ---------------------------------------------------------------- cleanup

    @staticmethod
    def _deduplicate(gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Keeps the worst instance of each gap category.

        With several competitors the same weakness surfaces once per rival.
        The reviewer wants one decision per problem, against whoever exposes it
        most sharply, not the same gap three times.
        """
        rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
        best: dict[str, dict[str, Any]] = {}
        for gap in gaps:
            key = gap["category"]
            current = best.get(key)
            if current is None or rank[gap["priority"]] > rank[current["priority"]]:
                best[key] = gap
        return sorted(
            best.values(), key=lambda gap: rank[gap["priority"]], reverse=True
        )


def _format(value: Any, unit: str | None) -> str:
    if value is None:
        return "not available"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        text = f"{value:,.2f}".rstrip("0").rstrip(".")
    else:
        text = str(value)
    return f"{text} {unit}".strip() if unit else text
