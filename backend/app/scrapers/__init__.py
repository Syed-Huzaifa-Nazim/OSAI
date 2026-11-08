"""Platform scrapers.

One self-contained folder per platform, plus the contract and registry they
share. Nothing here imports from the pipeline, the agents or the repository, so
a scraper can be exercised on its own; the dependency runs one way only.

    base.py       the two scraper contracts and their result types
    registry.py   key -> scraper, and the list the frontend renders
    daraz/        the Daraz.pk product scraper
    alibaba/      the Alibaba product scraper
    website/      crawls a site: pages, headings, links, readable text
    instagram/    a public Instagram profile's posts, via Apify

Product scrapers (Daraz, Alibaba) answer :class:`ProductScraper`; the website
and Instagram scrapers answer :class:`SourceScraper`, whose unit is a page or a
post rather than a listing.
"""

from __future__ import annotations

from app.scrapers.base import (
    COMPETITOR,
    OWN,
    PlatformInfo,
    ProductScraper,
    ScrapedDocument,
    ScrapedProductRecord,
    ScrapedSourceRecord,
    ScraperError,
    SourceScraper,
)
from app.scrapers.registry import (
    available_platforms,
    get_scraper,
    get_source_scraper,
    is_source_supported,
    is_supported,
    platform_keys,
    register,
    register_source,
    source_kind_for,
    source_kinds,
)

__all__ = [
    "COMPETITOR",
    "OWN",
    "PlatformInfo",
    "ProductScraper",
    "ScrapedDocument",
    "ScrapedProductRecord",
    "ScrapedSourceRecord",
    "ScraperError",
    "SourceScraper",
    "available_platforms",
    "get_scraper",
    "get_source_scraper",
    "is_source_supported",
    "is_supported",
    "platform_keys",
    "register",
    "register_source",
    "source_kind_for",
    "source_kinds",
]
