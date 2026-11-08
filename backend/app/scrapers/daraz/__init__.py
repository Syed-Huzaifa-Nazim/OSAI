"""Daraz.pk scraper.

Everything Daraz-specific lives in this folder and nowhere else:

    scraper.py    the scraping pipeline (requests/BS4 -> Playwright fallback)
    images.py     product photo extraction, run inside the same pass
    selectors.py  every CSS selector, JSON path and keyword list
    utils.py      generic parsing primitives used by scraper.py
    metrics.py    the A-H comparison parameters for Daraz metadata

``scraper.py``, ``selectors.py`` and ``utils.py`` are the standalone scraper's
files. Their extraction logic is unchanged; only the settings import was
repointed at the project's own config. This module is the thin adapter that
presents them through the platform-neutral :class:`ProductScraper` contract.
"""

from __future__ import annotations

from typing import Any

from app.scrapers.base import ProductScraper, ScrapedProductRecord, ScraperError
from app.scrapers.daraz import metrics
from app.scrapers.daraz.scraper import (
    TEXT_FIELD_TYPES,
    ScrapeError,
    _validate_url,
    canonical_url,
    scrape_daraz_product,
)


class DarazProductScraper(ProductScraper):
    platform = "daraz"
    label = "Daraz"
    url_hint = "A Daraz product page link"
    url_example = "https://www.daraz.pk/products/example-i123456789-s987654321.html"

    #: The text fields this platform produces. Stage 3 embeds each one as its
    #: own set of chunks so retrieval can be scoped to, say, reviews only.
    text_field_types = tuple(TEXT_FIELD_TYPES)

    def canonical_url(self, url: str) -> str:
        return canonical_url(url)

    def validate_url(self, url: str) -> None:
        """Host and scheme check only -- the same one the scraper runs first.

        Deliberately does not fetch anything: intake validation has to be
        instant, and whether the page actually resolves is stage 2's problem.
        """
        try:
            _validate_url((url or "").strip())
        except ScrapeError as exc:
            raise ScraperError(str(exc)) from exc

    def scrape(self, url: str, role: str) -> ScrapedProductRecord:
        """Runs the scraper and repackages its result.

        ``ScrapeError`` becomes ``ScraperError`` so callers only ever handle the
        platform-neutral exception.
        """
        try:
            product = scrape_daraz_product(url, role)
        except ScrapeError as exc:
            raise ScraperError(str(exc)) from exc

        return ScrapedProductRecord(
            role=role,
            platform=self.platform,
            url=product.url,
            product_name=product.product_name,
            text_fields=dict(product.text_fields),
            metadata=dict(product.metadata),
            method=product.method,
            warnings=list(product.warnings),
            images=[
                {"url": image.url, "position": position, "source": image.source}
                for position, image in enumerate(product.images, start=1)
            ],
        )

    def comparison_parameters(self) -> list[dict[str, Any]]:
        return metrics.PARAMETERS

    def build_metrics(
        self, own: dict[str, Any], competitor: dict[str, Any]
    ) -> list[dict[str, Any]]:
        return metrics.compare_all(own, competitor)


__all__ = ["DarazProductScraper", "metrics", "TEXT_FIELD_TYPES"]
