"""Stage 2: Scout Agent for e-commerce comparisons.

LIVE IMPLEMENTATION. Unlike the website/social Scout this one really does go
out and fetch pages, through the scrapers in ``app/scrapers/``.

It knows nothing about any particular marketplace. It asks the registry for the
project's platform and calls the contract; Daraz's selectors, its Playwright
fallback and its review endpoint are all behind that boundary. Adding Amazon
means adding a scraper, not editing this file.

Two things about how it runs:

  * Scrapers are synchronous, because Playwright's sync API refuses to run
    inside an event loop. Each one is dispatched with ``asyncio.to_thread``.
  * The user's own listing and the competitors' are scraped concurrently, but
    the Daraz scraper serialises its own browser launches internally
    (PLAYWRIGHT_SERIALIZE), so two Chromium instances never fight for CPU.

Output follows the stage-2 contract: ``payload`` is the ScrapedSource rows the
runner writes to ``scraped_sources``, and the full product records ride in
``artifacts["ecommerce_products"]``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.api.v1.agents.base import AgentResult, BaseAgent
from app.core.errors import ConflictError
from app.scrapers import COMPETITOR, OWN, ScrapedProductRecord, ScraperError, get_scraper
from app.services import demo_data
from app.services.repository import new_id

logger = logging.getLogger("optistratix.agents.scout.ecommerce")


class EcommerceScoutAgent(BaseAgent):
    name = "Scout Agent (e-commerce)"
    stage = 2
    is_live = True

    async def run(self, context: dict[str, Any]) -> AgentResult:
        started = time.perf_counter()
        project_id: str = context["project_id"]
        project: dict[str, Any] = context.get("project") or {}
        competitors: list[dict[str, Any]] = context.get("competitors", [])

        platform = project.get("ecommerce_platform")
        own_url = (project.get("brand_website") or "").strip()

        if not platform:
            raise ConflictError("This project has no e-commerce platform set.")
        if not own_url:
            raise ConflictError(
                "This project has no product link of your own, so there is nothing to compare."
            )
        if not competitors:
            raise ConflictError("This project has no competitor to compare against.")

        scraper = get_scraper(platform)
        logger.info(
            "Scout (%s) scraping project=%s competitors=%d", platform, project_id, len(competitors)
        )

        # One job per listing: the user's own, then one per competitor.
        jobs: list[tuple[str, str, dict[str, Any] | None]] = [(own_url, OWN, None)]
        jobs += [
            (competitor.get("landing_page_url", ""), COMPETITOR, competitor)
            for competitor in competitors
        ]

        scraped = await asyncio.gather(
            *(asyncio.to_thread(self._scrape_one, scraper, url, role) for url, role, _ in jobs),
            return_exceptions=True,
        )

        sources: list[dict[str, Any]] = []
        products: list[dict[str, Any]] = []
        images: list[dict[str, Any]] = []
        warnings: list[str] = []
        failures: list[str] = []

        for (url, role, competitor), result in zip(jobs, scraped):
            who = "Your listing" if role == OWN else f"Competitor '{competitor.get('name', '?')}'"

            if isinstance(result, ScraperError):
                failures.append(f"{who}: {result}")
                continue
            if isinstance(result, BaseException):
                logger.exception("Unexpected scrape failure for %s", url, exc_info=result)
                failures.append(
                    f"{who}: unexpected error ({result.__class__.__name__}: {result})"
                )
                continue

            source_id = new_id("src")
            scraped_at = demo_data.iso()

            sources.append({
                "id": source_id,
                "project_id": project_id,
                "competitor_id": competitor["id"] if competitor else None,
                "kind": "ecommerce_product",
                "url": result.url,
                "title": result.product_name,
                "excerpt": result.excerpt,
                # Stage 3 does the embedding, so the row is honest about it.
                "status": "scraped",
                "chunk_count": 0,
                "scraped_at": scraped_at,
            })

            product_row = self._to_product_row(
                project_id=project_id,
                source_id=source_id,
                competitor=competitor,
                record=result,
                scraped_at=scraped_at,
            )
            products.append(product_row)
            images.extend(self._to_image_rows(project_id, product_row["id"], result))
            warnings.extend(f"{who}: {warning}" for warning in result.warnings)

        # The user's own listing is not optional: without it there is no
        # baseline, and every downstream comparison would be meaningless.
        own_scraped = any(product["role"] == OWN for product in products)
        if failures and not own_scraped:
            raise ScraperError(" | ".join(failures))
        if not any(product["role"] == COMPETITOR for product in products):
            raise ScraperError(
                "No competitor listing could be scraped, so there is nothing to compare against. "
                + (" | ".join(failures) if failures else "")
            )
        # Partial success: a competitor we could not read is a warning, not a
        # failed run, because the comparison still works on the ones we got.
        warnings.extend(failures)

        return AgentResult(
            payload=sources,
            artifacts={"ecommerce_products": products, "ecommerce_product_images": images},
            items_processed=len(sources),
            duration_ms=self._elapsed_ms(started),
            # No LLM calls happen here; the UI renders a dash rather than a zero.
            tokens_used=None,
            cost_usd=None,
            warnings=warnings,
        )

    @staticmethod
    def _scrape_one(scraper: Any, url: str, role: str) -> ScrapedProductRecord:
        """Runs in a worker thread. Exceptions come back through gather()."""
        return scraper.scrape(url, role)

    @staticmethod
    def _to_image_rows(
        project_id: str, product_id: str, record: ScrapedProductRecord
    ) -> list[dict[str, Any]]:
        """One ``ecommerce_product_images`` row per photo, in gallery order.

        Only the platform's own image URLs are stored; nothing is downloaded.
        """
        rows: list[dict[str, Any]] = []
        for image in record.images:
            url = (image.get("url") or "").strip()
            if not url:
                continue
            position = len(rows) + 1
            rows.append({
                "id": new_id("img"),
                "product_id": product_id,
                "project_id": project_id,
                "position": position,
                "url": url,
                "is_primary": position == 1,
                "source": image.get("source") or "gallery",
            })
        return rows

    @staticmethod
    def _to_product_row(
        *,
        project_id: str,
        source_id: str,
        competitor: dict[str, Any] | None,
        record: ScrapedProductRecord,
        scraped_at: str,
    ) -> dict[str, Any]:
        """Flattens a scraped record into an ``ecommerce_products`` row.

        The common fields become real columns; the complete scraper output is
        kept in ``raw_metadata`` so nothing the scraper found is lost, and so
        the comparison engine still sees every field it expects.
        """
        meta = record.metadata
        return {
            "id": new_id("prod"),
            "project_id": project_id,
            "competitor_id": competitor["id"] if competitor else None,
            "source_id": source_id,
            "platform": record.platform,
            "role": record.role,
            "url": record.url,
            "product_name": record.product_name,
            "brand": meta.get("brand"),
            "price": meta.get("price"),
            "original_price": meta.get("original_price"),
            "discount_percent": meta.get("discount_percent"),
            "currency": "PKR",
            "rating": meta.get("rating"),
            "review_count": meta.get("review_count") or 0,
            "image_count": meta.get("image_count") or 0,
            "seller_name": meta.get("seller_name"),
            "seller_rating": meta.get("seller_rating"),
            "stock_status": meta.get("stock_status"),
            "category": meta.get("category"),
            "content_completeness_score": meta.get("content_completeness_score"),
            "text_fields": record.text_fields,
            "raw_metadata": meta,
            "scrape_method": record.method,
            "warnings": record.warnings[:6],
            "chunk_count": 0,
            "scraped_at": scraped_at,
        }
