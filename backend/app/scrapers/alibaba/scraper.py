"""Alibaba product scraper.

Strategy
--------
A pasted product link is not fetched: Alibaba answers product-detail pages with
a CAPTCHA to every automated client (plain HTTP and a headless browser alike,
measured 2026-09-11), and this scraper never tries to defeat that. Instead:

1. Read the product id and title words from the link.
2. Search the permitted listing surface (wholesaler.alibaba.com/w/...) with
   those words, trying a few wordings. robots.txt is checked before every
   request, requests are paced, and the client identifies itself honestly.
3. Each page is fetched with `requests` + parsed from its embedded JSON
   (BeautifulSoup reads the product cards if the JSON is missing). If the page
   fails or comes back without products, it is rendered once with Playwright,
   the same fallback the Daraz scraper uses.
4. The offer whose id matches the link becomes the product record.

An anti-bot page is recognised and reported. It is never retried past, solved
or worked around.

Every selector / path / keyword lives in selectors.py.
"""

from __future__ import annotations

import contextlib
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

from app.core.config import settings
from . import selectors as S
from .extract import TEXT_FIELD_TYPES, extract_offer
from .images import ProductImage
from .listing import ListingPage, detect_challenge, parse_listing
from .robots import RobotsDisallowed, RobotsPolicy
from .urls import InvalidAlibabaUrl, listing_url, parse_product_link, search_slugs

log = logging.getLogger(__name__)

__all__ = ["ScrapeError", "ScrapedProduct", "scrape_alibaba_product", "TEXT_FIELD_TYPES"]


class ScrapeError(Exception):
    """A product could not be scraped. The message is written for the user."""


@dataclass
class ScrapedProduct:
    url: str
    product_id: str                             # "own" | "competitor"
    text_fields: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    method: str = "unknown"                     # "bs4" | "playwright" | "bs4+playwright"
    warnings: List[str] = field(default_factory=list)
    images: List[ProductImage] = field(default_factory=list)
    price_tiers: List[Dict[str, Any]] = field(default_factory=list)
    supplier: Optional[Dict[str, Any]] = None

    @property
    def product_name(self) -> str:
        return self.metadata.get("product_name") or "Unknown product"


_robots = RobotsPolicy(S.USER_AGENT, timeout_seconds=15.0)

# Requests to Alibaba are strictly sequential across the whole process -- the
# user's listing and the competitor's are scraped in parallel threads, and this
# is what keeps them from arriving at the site together.
_pace_lock = threading.Lock()
_last_request_at = 0.0

# One headless browser at a time, as with the Daraz fallback.
_playwright_lock = threading.Lock()

_BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def scrape_alibaba_product(url: str, product_id: str) -> ScrapedProduct:
    """Scrape one Alibaba product, identified by its product link."""
    try:
        link = parse_product_link(url)
    except InvalidAlibabaUrl as exc:
        raise ScrapeError(str(exc)) from exc

    candidates = search_slugs(link.slug)
    if not candidates:
        raise ScrapeError(
            "That Alibaba link has no product title in it, so the product cannot be looked up. "
            "Open the product on Alibaba and copy the full link from the address bar."
        )
    candidates = candidates[: max(1, settings.alibaba_max_search_queries)]

    warnings: List[str] = []
    methods: set = set()
    challenged: Optional[str] = None

    for search_slug in candidates:
        page_url = listing_url(search_slug)
        try:
            page, method, notes = _load_listing(page_url)
        except RobotsDisallowed as exc:
            raise ScrapeError(
                f"Alibaba's robots.txt does not allow reading {page_url}, so this product cannot be "
                "collected. Nothing was fetched."
            ) from exc
        methods.add(method)
        warnings.extend(notes)

        if page.challenged:
            challenged = page.challenge_marker
            # A block is the site's answer. Stop rather than keep asking.
            break

        offer = page.offers.get(link.product_id)
        if offer is None:
            log.info("Alibaba product %s not in results for %r", link.product_id, search_slug)
            continue

        extracted = extract_offer(offer, from_page_data=page.from_page_data)
        metadata = extracted.metadata
        metadata["product_id"] = product_id
        metadata["product_name"] = extracted.text_fields["title"][:220]
        metadata["product_url"] = link.canonical_url
        metadata["item_id"] = link.product_id
        metadata["matched_search"] = search_slug

        return ScrapedProduct(
            url=link.canonical_url,
            product_id=product_id,
            text_fields=extracted.text_fields,
            metadata=metadata,
            method=_method_label(methods),
            warnings=warnings + extracted.warnings,
            images=extracted.images,
            price_tiers=extracted.price_tiers,
            supplier=extracted.supplier,
        )

    if challenged:
        raise ScrapeError(
            "Alibaba answered with an anti-bot verification page instead of product data. "
            "OptiStratixAI does not bypass these checks, so this listing could not be collected. "
            "Try again later."
        )
    raise ScrapeError(
        f"Alibaba product {link.product_id} could not be found on Alibaba's public wholesale "
        "listings, which are the only Alibaba pages this tool is allowed to read (product pages "
        "themselves are protected by a CAPTCHA). The product may not be listed there, or its "
        "link may be out of date. Try a different product link."
    )


def _method_label(methods: set) -> str:
    if methods == {"bs4"}:
        return "bs4"
    if methods == {"playwright"}:
        return "playwright"
    return "bs4+playwright" if methods else "unknown"


# ---------------------------------------------------------------------------
# Fetching one listing page
# ---------------------------------------------------------------------------
def _load_listing(page_url: str) -> tuple:
    """(ListingPage, method, warnings) for one listing URL.

    requests first; the browser only if that failed or returned no products.
    """
    _robots.require_allowed(page_url)
    notes: List[str] = []

    html: Optional[str] = None
    try:
        html = _fetch_with_requests(page_url)
    except (ScrapeError, RobotsDisallowed):
        # A refusal, or a redirect somewhere robots.txt forbids: a browser would
        # be sent to the same place, so there is no fallback.
        raise
    except Exception as exc:  # network, timeout, non-200
        notes.append(f"Listing fetch failed ({exc.__class__.__name__}); trying a browser render.")
        log.warning("requests fetch failed for %s: %s", page_url, exc)

    if html is not None:
        page = parse_listing(html)
        if page.offers or page.challenged:
            return page, "bs4", notes
        notes.append("The listing came back without product data; trying a browser render.")

    if not settings.scraper_enable_playwright:
        if html is None:
            raise ScrapeError(
                f"Could not load {page_url} and the browser fallback is disabled "
                "(SCRAPER_ENABLE_PLAYWRIGHT=false)."
            )
        return parse_listing(html), "bs4", notes

    try:
        rendered = _fetch_with_playwright(page_url)
    except RobotsDisallowed:
        raise
    except Exception as exc:
        log.warning("playwright fallback failed for %s: %s", page_url, exc)
        notes.append(f"Browser render failed ({exc.__class__.__name__}).")
        if html is None:
            raise ScrapeError(
                "Alibaba's listing could not be loaded, by a normal request or a browser. "
                "Check the connection and try again."
            ) from exc
        return parse_listing(html), "bs4", notes

    return parse_listing(rendered), ("playwright" if html is None else "bs4+playwright"), notes


def _pace(url: str) -> None:
    """Wait until the minimum gap since the previous Alibaba request has passed."""
    global _last_request_at
    delay = max(settings.alibaba_request_delay_seconds, _robots.crawl_delay(url) or 0.0)
    wait = _last_request_at + delay - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.monotonic()


def _fetch_with_requests(url: str) -> str:
    for attempt in (1, 2):
        with _pace_lock:
            _pace(url)
            response = requests.get(
                url, headers=S.REQUEST_HEADERS, timeout=settings.scraper_timeout, allow_redirects=True
            )

        if response.status_code in S.RATE_LIMIT_STATUS_CODES and attempt == 1:
            log.info("Alibaba rate limited %s (HTTP %s); backing off once", url, response.status_code)
            time.sleep(S.RATE_LIMIT_BACKOFF_SECONDS)
            continue
        if response.status_code in S.RATE_LIMIT_STATUS_CODES:
            raise ScrapeError(
                f"Alibaba is rate limiting requests right now (HTTP {response.status_code}). "
                "Try again in a few minutes."
            )
        if response.status_code in S.BLOCKED_STATUS_CODES:
            raise ScrapeError(
                f"Alibaba refused the request (HTTP {response.status_code}). "
                "OptiStratixAI does not work around refusals, so this listing could not be collected."
            )
        if response.url and response.url != url:
            # A redirect to somewhere robots.txt forbids is still a forbidden fetch.
            _robots.require_allowed(response.url)
        response.raise_for_status()
        return response.text
    raise ScrapeError("Alibaba did not answer the listing request.")  # pragma: no cover


def _fetch_with_playwright(url: str) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover
        raise ScrapeError(
            "Playwright is not installed. Run: pip install playwright && python -m playwright install chromium"
        ) from exc

    _robots.require_allowed(url)
    lock = _playwright_lock if settings.playwright_serialize else contextlib.nullcontext()
    with lock, _pace_lock:
        _pace(url)
        return _playwright_render(sync_playwright, url)


def _playwright_render(sync_playwright, url: str) -> str:
    """A normal page load. No stealth patches, no fingerprint changes."""
    timeout_ms = settings.playwright_timeout * 1000
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            context = browser.new_context(user_agent=S.USER_AGENT, locale="en-US")
            if settings.playwright_block_media:
                context.route(
                    "**/*",
                    lambda route: (
                        route.abort()
                        if route.request.resource_type in _BLOCKED_RESOURCE_TYPES
                        else route.continue_()
                    ),
                )
            page = context.new_page()
            page.set_default_timeout(timeout_ms)
            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            if page.url and page.url != url:
                # Redirected: what it landed on must be permitted too, or the
                # page is not read.
                _robots.require_allowed(page.url)

            with contextlib.suppress(Exception):
                page.wait_for_function(
                    "() => typeof window._PAGE_DATA_ === 'object' && window._PAGE_DATA_ !== null",
                    timeout=S.PLAYWRIGHT_PAGE_DATA_TIMEOUT_MS,
                )
            html = page.content()
            if S.PAGE_DATA_MARKER not in html:
                # The object may have been assigned by a script that is no
                # longer inline; serialise it straight from the page.
                with contextlib.suppress(Exception):
                    payload = page.evaluate("() => JSON.stringify(window._PAGE_DATA_ || null)")
                    if payload and payload != "null" and not detect_challenge(html):
                        html = f"<script>{S.PAGE_DATA_MARKER} = {payload};</script>{html}"
            return html
        finally:
            browser.close()
