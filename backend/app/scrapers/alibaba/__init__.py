"""Alibaba scraper.

Everything Alibaba-specific lives in this folder and nowhere else:

    scraper.py    orchestration: link -> permitted listing search -> matching offer
    listing.py    reading a listing page (embedded JSON, markup fallback, block detection)
    extract.py    turning one offer into text fields, metadata, tiers and supplier profile
    images.py     product photo URLs, from the same offer
    urls.py       reading product links and building listing URLs
    robots.py     RFC 9309 robots.txt enforcement, checked before every request
    selectors.py  every host, path, JSON path and keyword
    metrics.py    the A-J comparison parameters for Alibaba metadata

This module is the thin adapter presenting them through the platform-neutral
ProductScraper contract, the same way the Daraz scraper is presented.
"""

from __future__ import annotations

from typing import Any

from app.scrapers.base import ProductScraper, ScrapedProductRecord, ScraperError
from app.scrapers.alibaba import metrics
from app.scrapers.alibaba.scraper import TEXT_FIELD_TYPES, ScrapeError, scrape_alibaba_product
from app.scrapers.alibaba.urls import InvalidAlibabaUrl, parse_product_link


class AlibabaProductScraper(ProductScraper):
    platform = "alibaba"
    label = "Alibaba"
    url_hint = "An Alibaba product page link"
    url_example = "https://www.alibaba.com/product-detail/Mini-Wireless-Mouse-Ergonomic-4-Buttons_1601364965690.html"

    text_field_types = tuple(TEXT_FIELD_TYPES)

    def canonical_url(self, url: str) -> str:
        """One key per product, whatever the link looks like.

        The product id alone decides identity: a desktop link, a mobile link and
        a link with a reworded title slug all name the same listing. This is an
        identity key for comparing links; the scraper stores the full
        title-bearing link for display.
        """
        try:
            return f"https://www.alibaba.com/product-detail/_{parse_product_link(url).product_id}.html"
        except InvalidAlibabaUrl:
            return (url or "").strip()

    def validate_url(self, url: str) -> None:
        """Shape check only -- the link is never fetched."""
        try:
            parse_product_link(url)
        except InvalidAlibabaUrl as exc:
            raise ScraperError(str(exc)) from exc

    def scrape(self, url: str, role: str) -> ScrapedProductRecord:
        try:
            product = scrape_alibaba_product(url, role)
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
            price_tiers=[dict(tier) for tier in product.price_tiers],
            supplier=dict(product.supplier) if product.supplier else None,
        )

    def comparison_parameters(self) -> list[dict[str, Any]]:
        return metrics.PARAMETERS

    def build_metrics(self, own: dict[str, Any], competitor: dict[str, Any]) -> list[dict[str, Any]]:
        return metrics.compare_all(own, competitor)


__all__ = ["AlibabaProductScraper", "metrics", "TEXT_FIELD_TYPES"]
