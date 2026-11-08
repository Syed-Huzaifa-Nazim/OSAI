"""Daraz.pk product scraper.

Strategy
--------
1. `requests` + BeautifulSoup4 on the raw HTML. Daraz server-renders a big
   inline JSON blob, so this alone usually yields every field.
2. If the required fields (title, price) are missing, re-fetch with Playwright
   (headless Chromium), let the SPA hydrate, and parse the rendered DOM.
3. Reviews come from Daraz's review JSON endpoint, which the PDP itself calls.

Every selector / path / keyword lives in selectors.py so that markup changes
only require editing that one file.
"""

from __future__ import annotations

import contextlib
import logging
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

from app.core.config import settings
from . import selectors as S
from .images import ProductImage, extract_product_images, image_identity
from .utils import (
    clean_text,
    collect_strings,
    contains_any,
    count_keyword_hits,
    dedupe_preserve_order,
    deep_get,
    extract_json_object,
    find_key_anywhere,
    first_path,
    matched_keywords,
    percent,
    safe_json_loads,
    strip_html,
    to_bool,
    to_float,
    to_int,
    truncate,
)

log = logging.getLogger(__name__)

# Text fields that become their own ChromaDB chunks.
TEXT_FIELD_TYPES = [
    "title",
    "description",
    "specs",
    "review",
    "promo_tags",
    "policy_text",
    "category",
]

REQUIRED_FIELDS = ("title", "price")


class ScrapeError(Exception):
    """Raised when a product page cannot be scraped by any method."""


@dataclass
class ScrapedProduct:
    url: str
    product_id: str                             # "own" | "competitor"
    text_fields: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    method: str = "unknown"
    warnings: List[str] = field(default_factory=list)
    #: Distinct product photos, main image first. Extracted in the same pass as
    #: everything else, from the HTML already fetched.
    images: List[ProductImage] = field(default_factory=list)

    @property
    def product_name(self) -> str:
        return self.metadata.get("product_name") or "Unknown product"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def scrape_daraz_product(url: str, product_id: str) -> ScrapedProduct:
    """Scrape one Daraz product page into text chunks + structured metadata."""
    url = (url or "").strip()
    _validate_url(url)
    url = canonical_url(url)

    warnings: List[str] = []
    html_doc: Optional[str] = None
    method = "bs4"

    try:
        html_doc = _fetch_with_requests(url)
    except Exception as exc:  # network, timeout, non-200
        warnings.append(f"HTTP fetch failed ({exc.__class__.__name__}: {exc}); trying Playwright.")
        log.warning("requests fetch failed for %s: %s", url, exc)

    product: Optional[ScrapedProduct] = None
    if html_doc:
        product = _parse_page(html_doc, url, product_id)
        product.method = "bs4"

    if product is None or not _has_required_fields(product):
        missing = _missing_fields(product)
        if product is not None:
            warnings.append(f"BS4 extraction incomplete (missing: {', '.join(missing)}); using Playwright.")
        if not settings.scraper_enable_playwright:
            if product is None:
                raise ScrapeError(
                    f"Could not fetch {url} and the Playwright fallback is disabled "
                    "(SCRAPER_ENABLE_PLAYWRIGHT=false)."
                )
            warnings.append("Playwright fallback disabled; returning partial data.")
        else:
            try:
                rendered = _fetch_with_playwright(url)
                rendered_product = _parse_page(rendered, url, product_id)
                if product is None:
                    product = rendered_product
                    product.method = "playwright"
                else:
                    _merge_products(product, rendered_product)
                    product.method = "bs4+playwright"
            except Exception as exc:
                warnings.append(f"Playwright fallback failed ({exc.__class__.__name__}: {exc}).")
                log.warning("playwright fallback failed for %s: %s", url, exc)

    if product is None:
        raise ScrapeError(
            f"Failed to scrape {url}. Both requests+BS4 and Playwright were unable to load the page. "
            "Check that the URL is a valid, reachable Daraz product page."
        )

    if not _has_required_fields(product):
        missing = _missing_fields(product)
        raise ScrapeError(
            f"Scraped {url} but could not extract required field(s): {', '.join(missing)}. "
            "The page may not be a product page, may be region-locked, or Daraz's layout may have "
            "changed (update backend/app/scrapers/daraz/selectors.py)."
        )

    _attach_reviews(product)
    _finalise(product)
    if not product.images:
        product.warnings.append("No product images were found on this listing.")
    product.warnings = warnings + product.warnings
    return product


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------
# Query parameters worth keeping; everything else on a Daraz product link is
# search/click tracking that bloats the request and slows rendering.
KEEP_QUERY_PARAMS = {"skuId", "spm_variant", "lang"}


def canonical_url(url: str) -> str:
    """Strip Daraz's search tracking parameters from a product link.

    Links copied out of Daraz search results carry a ~1.5KB `clickTrackInfo` /
    `priceCompare` blob. It is pure telemetry, it makes the page noticeably
    slower to render, and it means the same product yields different URLs on
    every copy. The canonical `/products/...-iXXXX-sYYYY.html` form is what we
    fetch and what we store.
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return url
    if "/products/" not in parsed.path:
        return url

    kept = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=False) if k in KEEP_QUERY_PARAMS]
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        urlencode(kept),
        "",  # drop the fragment
    ))


def _validate_url(url: str) -> None:
    if not url:
        raise ScrapeError("Product URL is empty.")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ScrapeError(f"Invalid URL '{url}': must start with http:// or https://")
    if not parsed.netloc:
        raise ScrapeError(f"Invalid URL '{url}': no host found.")
    if not any(fragment in parsed.netloc.lower() for fragment in S.ALLOWED_HOST_FRAGMENTS):
        raise ScrapeError(
            f"'{parsed.netloc}' is not a Daraz domain. This tool only supports Daraz product links "
            "(e.g. https://www.daraz.pk/products/...)."
        )


def _fetch_with_requests(url: str) -> str:
    response = requests.get(
        url,
        headers=S.REQUEST_HEADERS,
        timeout=settings.scraper_timeout,
        allow_redirects=True,
    )
    if response.status_code == 404:
        raise ScrapeError(f"Product not found (HTTP 404): {url}")
    response.raise_for_status()
    return response.text


# Only one headless browser at a time by default: two concurrent Chromium
# launches on a normal laptop starve each other and blow the navigation budget.
_playwright_lock = threading.Lock()

# Heavy assets we never parse. Aborting them cuts page load dramatically while
# leaving the <img>/<video> tags (and therefore image_count / has_video) intact.
_BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}


def _fetch_with_playwright(url: str) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover
        raise ScrapeError(
            "Playwright is not installed. Run: pip install playwright && python -m playwright install chromium"
        ) from exc

    lock = _playwright_lock if settings.playwright_serialize else contextlib.nullcontext()
    with lock:
        return _playwright_render(sync_playwright, url)


def _wait_for_price(page, price_selector: str) -> bool:
    """Wait until a price element exists AND actually carries digits."""
    try:
        page.wait_for_selector(price_selector, timeout=S.PLAYWRIGHT_PRICE_TIMEOUT_MS, state="attached")
    except Exception:
        return False

    # The element can mount empty for a beat while the value is filled in.
    deadline = S.PLAYWRIGHT_PRICE_TIMEOUT_MS
    waited = 0
    while waited < deadline:
        try:
            text = page.locator(price_selector).first.inner_text(timeout=2000)
        except Exception:
            text = ""
        if any(char.isdigit() for char in text):
            return True
        page.wait_for_timeout(500)
        waited += 500
    return False


def _playwright_render(sync_playwright, url: str) -> str:
    timeout_ms = settings.playwright_timeout * 1000

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        try:
            context = browser.new_context(
                user_agent=S.REQUEST_HEADERS["User-Agent"],
                locale="en-US",
                viewport={"width": 1440, "height": 900},
            )
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

            # "commit" returns as soon as the navigation is committed rather than
            # waiting on the whole subresource graph, which Daraz never finishes
            # quickly. The real readiness signal is the selector wait below.
            try:
                page.goto(url, timeout=timeout_ms, wait_until="commit")
            except Exception:
                page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")

            # Wait for the PRICE specifically. Waiting on <h1> is a trap: the
            # title is in the server HTML and resolves instantly, while the
            # price block hydrates seconds later - so an h1-only wait returns a
            # page that has no price on it.
            price_selector = ", ".join(S.CSS["price_now"])
            if not _wait_for_price(page, price_selector):
                # Price never appeared: reload once (Daraz intermittently serves
                # a shell on first hit) before giving up on it.
                try:
                    page.reload(timeout=timeout_ms, wait_until="domcontentloaded")
                    _wait_for_price(page, price_selector)
                except Exception:
                    pass

            if not page.locator(price_selector).count():
                # Still nothing - at least make sure the product body is there.
                for selector in S.PLAYWRIGHT_WAIT_SELECTORS:
                    try:
                        page.wait_for_selector(selector, timeout=10000)
                        break
                    except Exception:
                        continue

            # Lazy-loaded gallery / specs / reviews only render after scrolling.
            for _ in range(S.PLAYWRIGHT_SCROLL_STEPS):
                page.mouse.wheel(0, 1200)
                page.wait_for_timeout(300)

            # Nudge each lazy module into view so its content actually mounts.
            for selector in S.PLAYWRIGHT_LAZY_MODULES:
                try:
                    locator = page.locator(selector).first
                    if locator.count():
                        locator.scroll_into_view_if_needed(timeout=3000)
                        page.wait_for_timeout(600)
                except Exception:
                    continue

            page.wait_for_timeout(S.PLAYWRIGHT_SETTLE_MS)

            return page.content()
        finally:
            browser.close()


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def _parse_page(html_doc: str, url: str, product_id: str) -> ScrapedProduct:
    soup = BeautifulSoup(html_doc, "lxml")
    extractor = _Extractor(soup, html_doc, url, product_id)
    return extractor.run()


def _has_required_fields(product: Optional[ScrapedProduct]) -> bool:
    if product is None:
        return False
    return not _missing_fields(product)


def _missing_fields(product: Optional[ScrapedProduct]) -> List[str]:
    if product is None:
        return list(REQUIRED_FIELDS)
    missing = []
    if not product.text_fields.get("title"):
        missing.append("title")
    if product.metadata.get("price") in (None, 0, 0.0):
        missing.append("price")
    return missing


# Strings that mean "we found nothing", so a later pass is allowed to overwrite them.
PLACEHOLDER_VALUES = {
    "", "unknown", "none", "not stated", "not found", "no brand",
    "unknown seller", "unknown product", "category path not found",
    "title not found",
}


def _is_fillable(value: Any) -> bool:
    """True when a value carries no information and may be replaced."""
    if value in (None, "", 0, 0.0, False, []):
        return True
    return isinstance(value, str) and value.strip().lower() in PLACEHOLDER_VALUES


def _merge_products(base: ScrapedProduct, extra: ScrapedProduct) -> None:
    """Fill gaps in `base` from `extra` without discarding what BS4 already found.

    Only *raw* fields are merged. Everything derived from them (counts, ratios,
    labels) is recomputed afterwards by _recompute_derived, because mixing
    derived values from two different passes produces incoherent records.
    """
    for key, value in extra.text_fields.items():
        if len(value or "") > len(base.text_fields.get(key) or ""):
            base.text_fields[key] = value
    for key, value in extra.metadata.items():
        if _is_fillable(base.metadata.get(key)) and not _is_fillable(value):
            base.metadata[key] = value
    # Images: keep BS4's order, add anything only the rendered page had.
    seen = {image_identity(image.url) for image in base.images}
    for image in extra.images:
        if len(base.images) >= S.IMAGE_MAX_PER_PRODUCT:
            break
        if image_identity(image.url) not in seen:
            seen.add(image_identity(image.url))
            base.images.append(image)
    base.warnings.extend(extra.warnings)


# ---------------------------------------------------------------------------
# The extractor
# ---------------------------------------------------------------------------
class _Extractor:
    def __init__(self, soup: BeautifulSoup, raw_html: str, url: str, product_id: str):
        self.soup = soup
        self.raw_html = raw_html
        self.url = url
        self.product_id = product_id
        self.page_text = clean_text(soup.get_text(" ", strip=True))[:120_000]
        self.module: Dict[str, Any] = self._load_module_data()
        self.jsonld: Dict[str, Any] = self._load_jsonld()
        self.text: Dict[str, str] = {}
        self.meta: Dict[str, Any] = {}
        self.warnings: List[str] = []
        self.images: List[ProductImage] = []

    # -- source loading ----------------------------------------------------
    def _load_module_data(self) -> Dict[str, Any]:
        for pattern in S.JSON_BLOB_PATTERNS:
            for match in re.finditer(pattern, self.raw_html, flags=re.S):
                blob = extract_json_object(self.raw_html, match.start(1))
                if not isinstance(blob, dict):
                    continue
                for root in S.MODULE_DATA_ROOTS:
                    node = deep_get(blob, root)
                    if isinstance(node, dict) and len(node) > 1:
                        return node
                return blob
        return {}

    def _load_jsonld(self) -> Dict[str, Any]:
        for tag in self.soup.select(S.JSONLD_SELECTOR):
            data = safe_json_loads(tag.string or tag.get_text() or "")
            candidates = data if isinstance(data, list) else [data]
            for candidate in candidates:
                if isinstance(candidate, dict) and "Product" in str(candidate.get("@type", "")):
                    return candidate
        return {}

    # -- selector helpers --------------------------------------------------
    def _css_one(self, key: str) -> str:
        for selector in S.CSS.get(key, []):
            try:
                node = self.soup.select_one(selector)
            except Exception:
                continue
            if node:
                value = clean_text(node.get_text(" ", strip=True))
                if value:
                    return value
        return ""

    def _css_all(self, key: str, limit: int = 100) -> List[str]:
        for selector in S.CSS.get(key, []):
            try:
                nodes = self.soup.select(selector)
            except Exception:
                continue
            if nodes:
                values = [clean_text(n.get_text(" ", strip=True)) for n in nodes[:limit]]
                values = [v for v in values if v]
                if values:
                    return values
        return []

    def _css_count(self, key: str, limit: int = 400) -> int:
        for selector in S.CSS.get(key, []):
            try:
                nodes = self.soup.select(selector)
            except Exception:
                continue
            if nodes:
                return min(len(nodes), limit)
        return 0

    def _json(self, key: str, default: Any = None) -> Any:
        return first_path(self.module, S.JSON_PATHS.get(key, []), default)

    def _regex(self, key: str, haystack: Optional[str] = None) -> Optional[str]:
        pattern = S.TEXT_PATTERNS.get(key)
        if not pattern:
            return None
        match = re.search(pattern, haystack if haystack is not None else self.page_text, flags=re.I)
        if not match:
            return None
        for group in match.groups():
            if group:
                return group
        return match.group(0)

    # -- orchestration -----------------------------------------------------
    def run(self) -> ScrapedProduct:
        self._extract_identity()
        self._extract_pricing()
        self._extract_content()
        self._extract_social_proof()
        self._extract_availability_trust()
        self._extract_promotions()
        self._extract_variants()
        self._extract_category_and_seo()

        return ScrapedProduct(
            url=self.url,
            product_id=self.product_id,
            text_fields=self.text,
            metadata=self.meta,
            warnings=self.warnings,
            images=self.images,
        )

    # -- A/B: identity + pricing ------------------------------------------
    def _extract_identity(self) -> None:
        title = (
            clean_text(self._json("title"))
            or clean_text(self.jsonld.get("name"))
            or self._css_one("title")
            or clean_text(self.soup.title.string if self.soup.title else "")
        )
        title = re.sub(r"\s*[|\-–]\s*(Buy online|Daraz\.pk|Daraz).*$", "", title, flags=re.I).strip()
        self.text["title"] = title

        brand = (
            clean_text(self._json("brand"))
            or clean_text(deep_get(self.jsonld, "brand.name"))
            or self._css_one("brand")
        )
        if brand.lower() in {"no brand", "nobrand", "generic", ""}:
            brand = brand or "No Brand"
        self.meta["brand"] = brand or "No Brand"
        self.meta["is_branded"] = bool(brand) and brand.lower() not in {"no brand", "nobrand", "generic"}

        self.meta["product_id"] = self.product_id
        self.meta["product_name"] = truncate(title, 220) or "Unknown product"
        self.meta["product_url"] = self.url

        item_id = self._json("item_id") or self._regex("item_id_query", self.url) or self._regex("item_id_path", self.url)
        self.meta["item_id"] = str(item_id) if item_id else ""

        seller_id = self._json("seller_id") or self._regex("seller_id_query", self.url) or self._regex("seller_id_path", self.url)
        self.meta["seller_id"] = str(seller_id) if seller_id else ""

    def _extract_pricing(self) -> None:
        price = to_float(self._json("price_now"))
        if price is None:
            price = to_float(deep_get(self.jsonld, "offers.price")) or to_float(deep_get(self.jsonld, "offers.0.price"))
        if price is None:
            price = to_float(self._css_one("price_now"))
        if price is None:
            price = to_float(self._regex("price"))
        self.meta["price"] = price

        was = to_float(self._json("price_was")) or to_float(self._css_one("price_was"))
        self.meta["original_price"] = was

        discount = to_float(self._json("discount_raw")) or to_float(self._css_one("discount"))
        if discount is None:
            discount = to_float(self._regex("discount"))
        if discount is None and was and price and was > price:
            discount = round(((was - price) / was) * 100, 2)
        self.meta["discount_percent"] = abs(discount) if discount is not None else None

        # Price per unit for quantity-based listings ("Pack of 6", "3 Pcs").
        quantity = self._detect_quantity(self.text.get("title", ""))
        self.meta["unit_quantity"] = quantity
        self.meta["price_per_unit"] = (
            round(price / quantity, 2) if price and quantity and quantity > 1 else None
        )

        shipping_text = self._css_one("shipping_fee") or ""
        blob = " ".join(filter(None, [shipping_text, self._css_one("delivery"), self.page_text[:20000]]))
        if contains_any(blob, S.FREE_SHIPPING_KEYWORDS):
            self.meta["shipping_cost"] = 0.0
            self.meta["shipping_cost_label"] = "Free"
        else:
            fee = to_float(shipping_text)
            self.meta["shipping_cost"] = fee
            self.meta["shipping_cost_label"] = shipping_text or ("Rs. %s" % fee if fee is not None else "Not stated")

        deal_types: List[str] = []
        if contains_any(blob + self.page_text[:40000], S.FLASH_SALE_KEYWORDS):
            deal_types.append("flash sale")
        if contains_any(self.page_text[:40000], S.COUPON_KEYWORDS):
            deal_types.append("coupon/voucher")
        if contains_any(self.text.get("title", "") + self.page_text[:40000], S.BUNDLE_KEYWORDS):
            deal_types.append("bundle")
        if self.meta.get("discount_percent") and not deal_types:
            deal_types.append("standard discount")
        self.meta["deal_type"] = ", ".join(deal_types) if deal_types else "none"

    @staticmethod
    def _detect_quantity(title: str) -> Optional[int]:
        for pattern in S.QUANTITY_PATTERNS:
            match = re.search(pattern, title or "", flags=re.I)
            if match:
                value = to_int(match.group(1))
                if value and 1 < value <= 500:
                    return value
        return None

    # -- C: content quality -----------------------------------------------
    def _extract_content(self) -> None:
        description = strip_html(self._json("description_html")) or strip_html(self._json("highlights_html"))
        if not description:
            description = clean_text(self.jsonld.get("description"))
        if not description:
            description = strip_html(self._css_html("description"))
        self.text["description"] = truncate(description, 20_000)

        specs = self._extract_specs()
        self.text["specs"] = truncate(specs, 12_000)

        # The photos themselves. A failure here costs the images, never the
        # rest of the listing.
        try:
            self.images = extract_product_images(self.soup, self.module, self.jsonld)
        except Exception as exc:  # noqa: BLE001 - defensive: markup is outside our control
            log.warning("image extraction failed for %s: %s", self.url, exc)
            self.warnings.append(f"Product images could not be read ({exc.__class__.__name__}).")
            self.images = []

        # Counted from the distinct photos when there are any. The older
        # counters below remain as a fallback: they tally gallery thumbnails,
        # which include duplicates, so they overstate a real gallery.
        image_count = len(self.images)
        images = self._json("images_raw")
        if not image_count and isinstance(images, list):
            image_count = len([i for i in images if i])
        if not image_count:
            image_count = self._css_count("images")
        if not image_count:
            image_count = len(dedupe_preserve_order(
                re.findall(r"https?://[^\"'\s]+?(?:_\d+x\d+q?\d*)?\.(?:jpg|jpeg|png|webp)", self.raw_html[:400_000])
            )[:60])
        self.meta["image_count"] = int(image_count)

        video = self._json("video_raw")
        has_video = bool(video) or self._css_count("video") > 0
        if not has_video:
            has_video = bool(re.search(r'"videoUrl"\s*:\s*"[^"]+"|\.mp4', self.raw_html[:400_000]))
        self.meta["has_video"] = bool(has_video)

        content_blob = " ".join([self.text.get("description", ""), specs, self.page_text[:30000]])
        self.meta["variant_chart_present"] = contains_any(content_blob, S.SIZE_CHART_KEYWORDS) or self._css_count("size_chart") > 0

        self.meta["description_length"] = len(self.text.get("description", ""))
        self.meta["description_word_count"] = len(self.text.get("description", "").split())
        self.meta["spec_count"] = specs.count("\n") + (1 if specs else 0)
        self.meta["bullet_count"] = specs.count("- ") + self.text.get("description", "").count("- ")

    def _css_html(self, key: str) -> str:
        for selector in S.CSS.get(key, []):
            try:
                node = self.soup.select_one(selector)
            except Exception:
                continue
            if node:
                return str(node)
        return ""

    def _extract_specs(self) -> str:
        lines: List[str] = []

        raw = self._json("specs_raw")
        if isinstance(raw, dict):
            for key, value in raw.items():
                lines.append(f"{clean_text(key)}: {clean_text(value)}")
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    name = clean_text(item.get("name") or item.get("key") or item.get("title"))
                    value = clean_text(item.get("value") or item.get("text") or item.get("content"))
                    lines.append(f"{name}: {value}" if name and value else (name or value))
                else:
                    lines.append(clean_text(item))
        elif isinstance(raw, str):
            lines.extend(strip_html(raw).split("\n"))

        if not lines:
            # Spec tables render as <li> / <tr> pairs in the specification module.
            for selector in S.CSS.get("specs", []):
                try:
                    container = self.soup.select_one(selector)
                except Exception:
                    continue
                if not container:
                    continue
                for row in container.select("li, tr"):
                    text_value = clean_text(row.get_text(" : ", strip=True))
                    if text_value:
                        lines.append(text_value)
                if lines:
                    break

        if not lines:
            props = self.jsonld.get("additionalProperty")
            if isinstance(props, list):
                for prop in props:
                    if isinstance(prop, dict):
                        lines.append(f"{clean_text(prop.get('name'))}: {clean_text(prop.get('value'))}")

        return "\n".join(f"- {ln}" if not ln.startswith("- ") else ln for ln in dedupe_preserve_order(lines))

    # -- D: social proof ---------------------------------------------------
    def _extract_social_proof(self) -> None:
        rating = to_float(self._json("rating_raw"))
        if rating is None:
            rating = to_float(deep_get(self.jsonld, "aggregateRating.ratingValue"))
        if rating is None:
            rating = to_float(find_key_anywhere(self.module, "average"))
        if rating is None:
            rating = to_float(self._css_one("rating"))
        if rating is None:
            rating = to_float(self._regex("rating"))
        self.meta["rating"] = round(rating, 2) if rating is not None and 0 <= rating <= 5 else None

        count = to_int(self._json("review_count_raw"))
        if count is None:
            count = to_int(deep_get(self.jsonld, "aggregateRating.reviewCount"))
        if count is None:
            count = to_int(deep_get(self.jsonld, "aggregateRating.ratingCount"))
        if count is None:
            count = to_int(self._css_one("review_count"))
        if count is None:
            count = to_int(self._regex("review_count"))
        self.meta["review_count"] = count if count is not None and count >= 0 else 0

        qa = to_int(self._json("qa_count_raw"))
        if qa is None:
            qa = to_int(self._css_one("qa_count"))
        if qa is None:
            qa = to_int(self._regex("qa_count"))
        self.meta["qa_count"] = qa if qa is not None and qa >= 0 else 0

        # In-page reviews (the API call in _attach_reviews usually supersedes this).
        review_texts = dedupe_preserve_order(self._css_all("reviews", limit=settings.scraper_max_reviews))
        if review_texts:
            self.text["review"] = "\n\n".join(review_texts)

    # -- E: availability & trust ------------------------------------------
    def _extract_availability_trust(self) -> None:
        stock_blob = " ".join([self._css_one("stock"), self.page_text[:30000]])
        availability = str(deep_get(self.jsonld, "offers.availability") or "")
        stock_value = to_int(self._json("stock_raw"))

        if contains_any(stock_blob, S.OUT_OF_STOCK_KEYWORDS) or "OutOfStock" in availability:
            stock_status = "out_of_stock"
        elif (stock_value is not None and 0 < stock_value <= 10) or contains_any(stock_blob, S.LIMITED_STOCK_KEYWORDS):
            stock_status = "limited"
        elif "InStock" in availability or stock_value or self.meta.get("price"):
            stock_status = "in_stock"
        else:
            stock_status = "unknown"
        self.meta["stock_status"] = stock_status
        self.meta["stock_quantity"] = stock_value

        delivery = self._css_one("delivery")
        if not delivery:
            delivery_raw = self._json("delivery_raw")
            delivery = " / ".join(collect_strings(delivery_raw, limit=6)) if delivery_raw else ""
        if not delivery:
            delivery = self._regex("delivery_days") or ""
        self.meta["delivery_estimate"] = truncate(clean_text(delivery), 160) or "Not stated"

        seller_rating = to_float(self._json("seller_rating_raw"))
        if seller_rating is None:
            seller_rating = to_float(self._css_one("seller_rating"))
        # Daraz shows seller quality as a percentage; normalise to 0-5 for comparability.
        if seller_rating is not None and seller_rating > 5:
            self.meta["seller_rating_percent"] = round(seller_rating, 2)
            seller_rating = round((seller_rating / 100) * 5, 2)
        else:
            self.meta["seller_rating_percent"] = round(seller_rating * 20, 2) if seller_rating else None
        self.meta["seller_rating"] = seller_rating

        seller_name = clean_text(self._json("seller_name")) or self._css_one("seller_name")
        self.meta["seller_name"] = seller_name or "Unknown seller"

        verified_blob = " ".join([seller_name, self._css_one("seller_badge"), self.page_text[:30000]])
        self.meta["seller_verified"] = to_bool(self._json("seller_verified")) or contains_any(
            verified_blob, S.VERIFIED_SELLER_KEYWORDS
        )

        policy_parts = [
            self._css_one("return_policy"),
            self._css_one("warranty"),
            " ".join(collect_strings(self._json("warranty_raw"), limit=10) or []),
        ]
        policy_text = "\n".join(p for p in policy_parts if p)
        if not policy_text:
            policy_text = self._harvest_sentences(S.RETURN_POLICY_KEYWORDS, limit=12)
        self.text["policy_text"] = truncate(policy_text, 6000)

    def _harvest_sentences(self, keywords: List[str], limit: int = 10) -> str:
        """Pull sentences mentioning given keywords out of the page text."""
        sentences = re.split(r"(?<=[.!?])\s+|\s{2,}", self.page_text)
        hits = [s.strip() for s in sentences if 15 < len(s) < 400 and contains_any(s, keywords)]
        return "\n".join(dedupe_preserve_order(hits)[:limit])

    # -- F: promotional signals -------------------------------------------
    def _extract_promotions(self) -> None:
        tags = self._css_all("promo_tags", limit=40)
        tags += collect_strings(self._json("promotions_raw"), limit=30) or []
        tags = [t for t in dedupe_preserve_order(tags) if 2 < len(t) < 200]

        haystack = " ".join([self.text.get("title", ""), " ".join(tags), self.page_text[:40000]])

        for keyword in S.BESTSELLER_KEYWORDS + S.FLASH_SALE_KEYWORDS:
            if keyword in haystack.lower() and keyword not in [t.lower() for t in tags]:
                tags.append(keyword.title())

        self.text["promo_tags"] = "\n".join(dedupe_preserve_order(tags)) or "No promotional badges found on this listing."

        self.meta["is_bestseller"] = contains_any(haystack, S.BESTSELLER_KEYWORDS)
        self.meta["has_bundle"] = contains_any(haystack, S.BUNDLE_KEYWORDS)
        self.meta["has_flash_sale"] = contains_any(haystack, S.FLASH_SALE_KEYWORDS)
        self.meta["has_coupon"] = contains_any(haystack, S.COUPON_KEYWORDS)
        self.meta["promo_tag_count"] = len(dedupe_preserve_order(tags))

        warranty_text = self._css_one("warranty") or self._regex("warranty") or ""
        warranty_blob = " ".join([warranty_text, self.text.get("policy_text", ""), self.text.get("specs", "")])
        has_warranty = "warranty" in warranty_blob.lower()
        if re.search(r"no warranty|warranty not available", warranty_blob, flags=re.I):
            has_warranty = False
        self.meta["warranty_present"] = has_warranty
        self.meta["warranty_text"] = truncate(clean_text(warranty_text), 200) or (
            "Warranty mentioned" if has_warranty else "Not stated"
        )

    # -- G: variants -------------------------------------------------------
    def _extract_variants(self) -> None:
        variant_count = 0
        variant_labels: List[str] = []

        raw = self._json("variants_raw")
        if isinstance(raw, list):
            for prop in raw:
                if isinstance(prop, dict):
                    values = prop.get("values") or prop.get("options") or []
                    if isinstance(values, list):
                        variant_count += len(values)
                    name = clean_text(prop.get("name") or prop.get("label"))
                    if name:
                        variant_labels.append(f"{name} ({len(values) if isinstance(values, list) else '?'})")
            if not variant_count:
                variant_count = len(raw)

        if not variant_count:
            variant_count = self._css_count("variants")

        self.meta["variant_count"] = int(variant_count)
        self.meta["variant_groups"] = ", ".join(variant_labels) if variant_labels else (
            f"{self._css_count('variant_groups')} option group(s)" if self._css_count("variant_groups") else "None"
        )

        custom_blob = " ".join([
            self.text.get("title", ""),
            self.text.get("description", "")[:4000],
            self.text.get("specs", "")[:2000],
        ])
        self.meta["customizable"] = contains_any(custom_blob, S.CUSTOMIZABLE_KEYWORDS)

    # -- B/H: category + SEO ----------------------------------------------
    def _extract_category_and_seo(self) -> None:
        crumbs = self._css_all("breadcrumb", limit=12)
        if not crumbs:
            raw = self._json("breadcrumb_raw")
            crumbs = collect_strings(raw, limit=12) if raw else []
        if not crumbs:
            crumbs = [clean_text(self.jsonld.get("category"))] if self.jsonld.get("category") else []
        crumbs = [c for c in dedupe_preserve_order(crumbs) if c.lower() not in {"home", "daraz"}]

        category_path = " > ".join(crumbs)
        self.text["category"] = category_path or "Category path not found"
        self.meta["category"] = category_path or "Unknown"
        self.meta["category_leaf"] = crumbs[-1] if crumbs else "Unknown"
        self.meta["category_depth"] = len(crumbs)

        title = self.text.get("title", "")
        words = [w for w in re.findall(r"[a-z0-9]+", title.lower()) if w not in S.TITLE_STOPWORDS]
        unique_words = set(words)
        self.meta["title_length"] = len(title)
        self.meta["title_word_count"] = len(title.split())
        self.meta["title_keyword_count"] = len(unique_words)
        self.meta["title_keyword_density"] = (
            round(len(unique_words) / len(title.split()) * 100, 2) if title.split() else 0.0
        )
        self.meta["title_top_keywords"] = ", ".join(sorted(unique_words, key=len, reverse=True)[:8])

        # How well the title's vocabulary matches where the product is filed.
        category_words = {w for w in re.findall(r"[a-z0-9]+", category_path.lower()) if w not in S.TITLE_STOPWORDS}
        overlap = len(unique_words & category_words)
        score = round(overlap / len(category_words) * 100, 2) if category_words else 0.0
        self.meta["category_tag_match_score"] = score
        if not category_words:
            label = "unknown"
        elif score >= 50:
            label = "high"
        elif score >= 20:
            label = "medium"
        else:
            label = "low"
        self.meta["category_tag_match"] = label


# ---------------------------------------------------------------------------
# Reviews (separate JSON endpoint)
# ---------------------------------------------------------------------------
def _attach_reviews(product: ScrapedProduct) -> None:
    item_id = product.metadata.get("item_id")
    collected: List[str] = []

    if item_id:
        session = requests.Session()
        session.headers.update({**S.REQUEST_HEADERS, "Accept": "application/json,text/plain,*/*"})
        session.headers["Referer"] = product.url
        payload: Any = None
        page = 1
        while len(collected) < settings.scraper_max_reviews and page <= 3:
            try:
                response = session.get(
                    S.REVIEW_API_TEMPLATE.format(item_id=item_id, page=page),
                    timeout=settings.scraper_timeout,
                )
                response.raise_for_status()
                # Daraz now answers this route with the PDP page for some
                # storefronts; anything that is not JSON means the endpoint is
                # gone and the on-page reviews are all we get.
                if "json" not in response.headers.get("content-type", "").lower():
                    product.warnings.append(
                        "Daraz review endpoint returned HTML rather than JSON; "
                        "using reviews rendered on the product page instead."
                    )
                    break
                payload = response.json()
            except Exception as exc:
                product.warnings.append(
                    f"Review endpoint unavailable ({exc.__class__.__name__}); using on-page reviews instead."
                )
                break

            items = deep_get(payload, "model.items") or deep_get(payload, "data.items") or []
            if not isinstance(items, list) or not items:
                break
            for item in items:
                if not isinstance(item, dict):
                    continue
                body = clean_text(item.get("reviewContent") or item.get("content") or "")
                if not body:
                    continue
                stars = item.get("rating") or item.get("star")
                prefix = f"[{stars}/5] " if stars else ""
                collected.append(prefix + body)
            page += 1

        ratings_total = deep_get(payload, "model.ratings.total") if payload else None
        if to_int(ratings_total) and not product.metadata.get("review_count"):
            product.metadata["review_count"] = to_int(ratings_total)

    if collected:
        product.text_fields["review"] = "\n\n".join(dedupe_preserve_order(collected)[: settings.scraper_max_reviews])

    review_text = product.text_fields.get("review", "")
    if not review_text:
        product.text_fields["review"] = "No customer reviews were retrievable for this listing."
        product.metadata["reviews_scraped"] = 0
    else:
        product.metadata["reviews_scraped"] = review_text.count("\n\n") + 1

    positive = count_keyword_hits(review_text, S.POSITIVE_REVIEW_WORDS)
    negative = count_keyword_hits(review_text, S.NEGATIVE_REVIEW_WORDS)
    total = positive + negative
    product.metadata["review_positive_hits"] = positive
    product.metadata["review_negative_hits"] = negative
    product.metadata["review_sentiment_score"] = round((positive - negative) / total, 3) if total else 0.0
    product.metadata["review_positive_themes"] = ", ".join(
        matched_keywords(review_text, S.POSITIVE_REVIEW_WORDS)[:8]
    ) or "none detected"
    product.metadata["review_negative_themes"] = ", ".join(
        matched_keywords(review_text, S.NEGATIVE_REVIEW_WORDS)[:8]
    ) or "none detected"


# ---------------------------------------------------------------------------
# Final touches
# ---------------------------------------------------------------------------
def _recompute_derived(product: ScrapedProduct) -> None:
    """Re-derive every computed metadata field from the final text fields.

    Runs after any BS4/Playwright merge so that counts, ratios and labels are
    always consistent with the text actually stored.
    """
    meta = product.metadata
    title = product.text_fields.get("title", "") or ""

    # --- images: a BS4 + Playwright merge can add photos, so recount ---
    if product.images:
        meta["image_count"] = len(product.images)

    # --- category path: split, de-duplicate, drop the trailing product title ---
    raw_path = product.text_fields.get("category", "") or ""
    crumbs = [c.strip() for c in re.split(r"\s*>\s*", raw_path) if c.strip()]
    crumbs = [c for c in crumbs if c.lower() not in {"home", "daraz", "category path not found"}]
    if crumbs and title and crumbs[-1][:40].strip().lower() == title[:40].strip().lower():
        crumbs = crumbs[:-1]
    crumbs = dedupe_preserve_order(crumbs)

    category_path = " > ".join(crumbs)
    product.text_fields["category"] = category_path or "Category path not found"
    meta["category"] = category_path or "Unknown"
    meta["category_leaf"] = crumbs[-1] if crumbs else "Unknown"
    meta["category_depth"] = len(crumbs)

    # --- title stats + category-tag relevance ---
    words = [w for w in re.findall(r"[a-z0-9]+", title.lower()) if w not in S.TITLE_STOPWORDS]
    unique_words = set(words)
    meta["title_length"] = len(title)
    meta["title_word_count"] = len(title.split())
    meta["title_keyword_count"] = len(unique_words)
    meta["title_keyword_density"] = (
        round(len(unique_words) / len(title.split()) * 100, 2) if title.split() else 0.0
    )
    meta["title_top_keywords"] = ", ".join(sorted(unique_words, key=len, reverse=True)[:8])

    category_words = {
        w for w in re.findall(r"[a-z0-9]+", category_path.lower()) if w not in S.TITLE_STOPWORDS
    }
    overlap = len(unique_words & category_words)
    score = round(overlap / len(category_words) * 100, 2) if category_words else 0.0
    meta["category_tag_match_score"] = score
    meta["category_tag_match"] = (
        "unknown" if not category_words else "high" if score >= 50 else "medium" if score >= 20 else "low"
    )

    # --- content volume ---
    description = product.text_fields.get("description", "") or ""
    specs = product.text_fields.get("specs", "") or ""
    meta["description_length"] = len(description)
    meta["description_word_count"] = len(description.split())
    meta["spec_count"] = specs.count("\n") + (1 if specs.strip() else 0)
    meta["bullet_count"] = specs.count("- ") + description.count("- ")

    # --- shipping label must agree with the numeric cost ---
    cost = meta.get("shipping_cost")
    label = str(meta.get("shipping_cost_label") or "")
    if cost == 0:
        meta["shipping_cost_label"] = "Free"
    elif cost is not None:
        if not any(char.isdigit() for char in label):
            meta["shipping_cost_label"] = f"Rs. {cost:,.0f}"
    elif not label or label.strip().lower() in PLACEHOLDER_VALUES:
        meta["shipping_cost_label"] = "Not stated"

    meta["is_branded"] = bool(meta.get("brand")) and str(meta["brand"]).lower() not in {
        "no brand", "nobrand", "generic", "unknown",
    }


def _finalise(product: ScrapedProduct) -> None:
    """Guarantee every declared text field exists and record content scores."""
    placeholders = {
        "title": "Title not found",
        "description": "No product description was found on this listing.",
        "specs": "No specification list was found on this listing.",
        "review": "No customer reviews were retrievable for this listing.",
        "promo_tags": "No promotional badges found on this listing.",
        "policy_text": "No return, refund or warranty text was found on this listing.",
        "category": "Category path not found",
    }
    _recompute_derived(product)

    for field_type in TEXT_FIELD_TYPES:
        value = (product.text_fields.get(field_type) or "").strip()
        product.text_fields[field_type] = value or placeholders[field_type]
        product.metadata[f"{field_type}_chars"] = len(value)

    # A simple 0-100 listing-completeness score, handy for the Content Quality view.
    checks = [
        product.metadata.get("description_length", 0) > 300,
        product.metadata.get("spec_count", 0) >= 5,
        product.metadata.get("image_count", 0) >= 4,
        bool(product.metadata.get("has_video")),
        bool(product.metadata.get("variant_chart_present")),
        product.metadata.get("review_count", 0) > 0,
        bool(product.metadata.get("warranty_present")),
        product.metadata.get("variant_count", 0) > 0,
    ]
    product.metadata["content_completeness_score"] = round(sum(checks) / len(checks) * 100, 1)
