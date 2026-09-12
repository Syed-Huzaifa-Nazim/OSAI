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
from app.scrapers.base import PlatformInfo, ProductScraper, ScraperError
from app.scrapers.daraz import DarazProductScraper

_SCRAPERS: dict[str, type[ProductScraper]] = {}


def register(scraper_class: type[ProductScraper]) -> type[ProductScraper]:
    """Adds a scraper to the registry. Returns it, so it can be used as a decorator."""
    if not scraper_class.platform:
        raise ValueError(f"{scraper_class.__name__} must declare a platform key")
    _SCRAPERS[scraper_class.platform] = scraper_class
    return scraper_class


register(DarazProductScraper)
register(AlibabaProductScraper)


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
