"""Platform scrapers.

One self-contained folder per platform, plus the contract and registry they
share. Nothing here imports from the pipeline, the agents or the repository, so
a scraper can be exercised on its own; the dependency runs one way only.

    base.py       the ProductScraper contract and its result type
    registry.py   platform key -> scraper, and the list the frontend renders
    daraz/        the Daraz.pk scraper
"""

from __future__ import annotations

from app.scrapers.base import (
    COMPETITOR,
    OWN,
    PlatformInfo,
    ProductScraper,
    ScrapedProductRecord,
    ScraperError,
)
from app.scrapers.registry import (
    available_platforms,
    get_scraper,
    is_supported,
    platform_keys,
    register,
)

__all__ = [
    "COMPETITOR",
    "OWN",
    "PlatformInfo",
    "ProductScraper",
    "ScrapedProductRecord",
    "ScraperError",
    "available_platforms",
    "get_scraper",
    "is_supported",
    "platform_keys",
    "register",
]
