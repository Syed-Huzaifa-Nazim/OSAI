"""Stage 2: Scout Agent for website and social comparisons.

LIVE IMPLEMENTATION. Unlike the mock Scout this one really does go out and
read pages, through the scrapers in ``app/scrapers/``.

It knows nothing about any particular site or network. It asks the registry
which source scraper the project needs -- the website crawler for a website
comparison, Instagram's Apify-backed scraper for a social one -- and calls the
contract. Adding Facebook later means adding a scraper, not editing this file.

Output follows the stage-2 contract: ``payload`` is the ``scraped_sources``
rows the runner writes, one per page or post, and the structured detail rows
ride in ``artifacts`` for the runner to store alongside them.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.api.v1.agents.base import AgentResult, BaseAgent
from app.core.errors import ConflictError
from app.scrapers import (
    COMPETITOR,
    OWN,
    ScrapedSourceRecord,
    ScraperError,
    get_source_scraper,
    source_kind_for,
)
from app.services import demo_data
from app.services.repository import new_id

logger = logging.getLogger("optistratix.agents.scout.source")

#: Which artifact each scraper's documents become. One table per kind, so a
#: page and a post are never squeezed into the same shape.
DETAIL_ARTIFACT = {
    "website": "website_pages",
    "instagram": "instagram_posts",
}

#: Rows that hang off one document, by the key the scraper filed them under:
#: ``(artifact, id prefix, the column pointing back at the parent row)``.
CHILD_ARTIFACTS = {
    "website": {
        "images": ("website_page_images", "wimg", "page_id"),
    },
    "instagram": {
        "media": ("instagram_post_media", "med", "post_id"),
        "comments": ("instagram_post_comments", "cmt", "post_id"),
    },
}

#: Detail-row id prefixes, per kind.
DETAIL_ID_PREFIX = {"website": "page", "instagram": "post"}


class SourceScoutAgent(BaseAgent):
    """Scrapes both sides of a website or social comparison."""

    name = "Scout Agent (website/social)"
    stage = 2
    is_live = True

    async def run(self, context: dict[str, Any]) -> AgentResult:
        started = time.perf_counter()
        project_id: str = context["project_id"]
        project: dict[str, Any] = context.get("project") or {}
        competitors: list[dict[str, Any]] = context.get("competitors", [])

        kind = source_kind_for(
            project.get("comparison_type") or "", project.get("social_platform")
        )
        own_url = (project.get("brand_website") or "").strip()

        if not kind:
            raise ConflictError("This project has nothing for the Scout Agent to read.")
        if not own_url:
            raise ConflictError(
                "This project has no link of your own, so there is nothing to compare."
            )
        if not competitors:
            raise ConflictError("This project has no competitor to compare against.")

        scraper = get_source_scraper(kind)
        logger.info(
            "Scout (%s) scraping project=%s competitors=%d", kind, project_id, len(competitors)
        )

        jobs: list[tuple[str, str, dict[str, Any] | None]] = [(own_url, OWN, None)]
        jobs += [
            (competitor.get("landing_page_url", ""), COMPETITOR, competitor)
            for competitor in competitors
        ]

        scraped = await asyncio.gather(
            *(asyncio.to_thread(scraper.scrape, url, role) for url, role, _ in jobs),
            return_exceptions=True,
        )

        sources: list[dict[str, Any]] = []
        details: list[dict[str, Any]] = []
        children: dict[str, list[dict[str, Any]]] = {}
        warnings: list[str] = []
        failures: list[str] = []

        for (url, role, competitor), result in zip(jobs, scraped):
            who = "Your link" if role == OWN else f"Competitor '{competitor.get('name', '?')}'"

            if isinstance(result, ScraperError):
                failures.append(f"{who}: {result}")
                continue
            if isinstance(result, BaseException):
                logger.exception("Unexpected scrape failure for %s", url, exc_info=result)
                failures.append(f"{who}: unexpected error ({result.__class__.__name__}: {result})")
                continue

            self._collect(project_id, kind, competitor, result, sources, details, children)
            warnings.extend(f"{who}: {warning}" for warning in result.warnings)

        # Without the user's own side there is no baseline, and every
        # comparison downstream would be meaningless.
        if failures and not any(row["competitor_id"] is None for row in sources):
            raise ScraperError(" | ".join(failures))
        if not any(row["competitor_id"] is not None for row in sources):
            raise ScraperError(
                "No competitor could be read, so there is nothing to compare against. "
                + (" | ".join(failures) if failures else "")
            )
        # Partial success is a warning, not a failed run: the comparison still
        # works on the sides that were read.
        warnings.extend(failures)

        artifacts: dict[str, Any] = {DETAIL_ARTIFACT[kind]: details}
        artifacts.update(children)

        return AgentResult(
            payload=sources,
            artifacts=artifacts,
            items_processed=len(sources),
            duration_ms=self._elapsed_ms(started),
            # No LLM calls happen here; the UI renders a dash rather than a zero.
            tokens_used=None,
            cost_usd=None,
            warnings=warnings,
        )

    @staticmethod
    def _collect(
        project_id: str,
        kind: str,
        competitor: dict[str, Any] | None,
        record: ScrapedSourceRecord,
        sources: list[dict[str, Any]],
        details: list[dict[str, Any]],
        children: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Turns one scraped link into its source rows and detail rows."""
        scraper = get_source_scraper(kind)
        scraped_at = demo_data.iso()
        competitor_id = competitor["id"] if competitor else None

        for document in record.documents:
            source_id = new_id("src")
            sources.append({
                "id": source_id,
                "project_id": project_id,
                "competitor_id": competitor_id,
                "kind": scraper.source_kind,
                "url": document.url or record.url,
                "title": (document.title or record.title)[:300],
                "excerpt": (document.excerpt or "")[:400],
                # Stage 3 does the embedding, so the row is honest about it.
                "status": "scraped",
                "chunk_count": 0,
                "scraped_at": scraped_at,
            })

            detail_id = new_id(DETAIL_ID_PREFIX[kind])
            details.append({
                "id": detail_id,
                "project_id": project_id,
                "source_id": source_id,
                "competitor_id": competitor_id,
                "role": record.role,
                "submitted_url": record.url,
                "text_fields": dict(document.text_fields),
                "scraped_at": scraped_at,
                **document.metadata,
            })

            for key, rows in document.children.items():
                mapping = CHILD_ARTIFACTS.get(kind, {}).get(key)
                if not mapping or not rows:
                    continue
                artifact, prefix, parent_key = mapping
                bucket = children.setdefault(artifact, [])
                for position, row in enumerate(rows, start=1):
                    bucket.append({
                        "id": new_id(prefix),
                        parent_key: detail_id,
                        "project_id": project_id,
                        "position": position,
                        **row,
                    })


class WebsiteScoutAgent(SourceScoutAgent):
    name = "Scout Agent (website)"


class SocialScoutAgent(SourceScoutAgent):
    name = "Scout Agent (social)"


__all__ = ["SourceScoutAgent", "WebsiteScoutAgent", "SocialScoutAgent"]
