"""Which scraper handles which platform.

The single lookup table the rest of the backend goes through. The Scout agent,
the intake validators and the ``/scrapers/platforms`` endpoint all read from
here, so a new marketplace becomes available everywhere at once:

    1. add ``app/scrapers/<platform>/`` with a :class:`ProductScraper`
    2. import and ``register()`` it below
    3. add the platform to the ``ecommerce_platform`` check constraint in a
       migration

Nothing else in the backend, and nothing in the frontend, needs editing: the
platform dropdown is served from :func:`available_platforms`.
"""

from __future__ import annotations

from app.scrapers.alibaba import AlibabaProductScraper
from app.scrapers.base import PlatformInfo, ProductScraper, ScraperError, SourceScraper
from app.scrapers.daraz import DarazProductScraper
from app.scrapers.instagram import InstagramSourceScraper
from app.scrapers.website import WebsiteSourceScraper

_SCRAPERS: dict[str, type[ProductScraper]] = {}
_SOURCE_SCRAPERS: dict[str, type[SourceScraper]] = {}


def register(scraper_class: type[ProductScraper]) -> type[ProductScraper]:
    """Adds a scraper to the registry. Returns it, so it can be used as a decorator."""
    if not scraper_class.platform:
        raise ValueError(f"{scraper_class.__name__} must declare a platform key")
    _SCRAPERS[scraper_class.platform] = scraper_class
    return scraper_class


register(DarazProductScraper)
register(AlibabaProductScraper)


def register_source(scraper_class: type[SourceScraper]) -> type[SourceScraper]:
    """Adds a website/social scraper to the registry."""
    if not scraper_class.kind:
        raise ValueError(f"{scraper_class.__name__} must declare a kind")
    _SOURCE_SCRAPERS[scraper_class.kind] = scraper_class
    return scraper_class


register_source(WebsiteSourceScraper)
register_source(InstagramSourceScraper)


def get_scraper(platform: str) -> ProductScraper:
    """Returns the scraper for ``platform``.

    Raises :class:`ScraperError` rather than KeyError so an unknown platform
    reaching the pipeline surfaces as a normal, user-readable stage failure.
    """
    scraper_class = _SCRAPERS.get((platform or "").strip().lower())
    if scraper_class is None:
        raise ScraperError(
            f"No scraper is registered for platform '{platform}'. "
            f"Available: {', '.join(sorted(_SCRAPERS)) or 'none'}."
        )
    return scraper_class()


def is_supported(platform: str | None) -> bool:
    return bool(platform) and platform.strip().lower() in _SCRAPERS


def available_platforms() -> list[PlatformInfo]:
    """Every registered platform, for the frontend's platform dropdown."""
    return [scraper_class.info() for scraper_class in _SCRAPERS.values()]


def platform_keys() -> list[str]:
    return sorted(_SCRAPERS)


# ------------------------------------------------- website / social sources --


def get_source_scraper(kind: str) -> SourceScraper:
    """Returns the scraper for a website or social comparison."""
    scraper_class = _SOURCE_SCRAPERS.get((kind or "").strip().lower())
    if scraper_class is None:
        raise ScraperError(
            f"No scraper is registered for '{kind}'. "
            f"Available: {', '.join(sorted(_SOURCE_SCRAPERS)) or 'none'}."
        )
    return scraper_class()


def source_kind_for(comparison_type: str, social_platform: str | None) -> str | None:
    """Which source scraper a project needs, or None if it needs none.

    The single place that maps a comparison onto a scraper: a website project
    is scraped by the website scraper, and a social project by its platform's.
    An e-commerce project uses a :class:`ProductScraper` instead, so it maps to
    nothing here.
    """
    comparison_type = (comparison_type or "").strip().lower()
    if comparison_type == "website":
        return "website"
    if comparison_type == "social_media":
        return (social_platform or "").strip().lower() or None
    return None


def is_source_supported(kind: str | None) -> bool:
    """True when a scraper exists for this kind AND can actually run."""
    scraper_class = _SOURCE_SCRAPERS.get((kind or "").strip().lower())
    return scraper_class is not None and scraper_class.is_available()


def source_kinds() -> list[str]:
    return sorted(_SOURCE_SCRAPERS)
