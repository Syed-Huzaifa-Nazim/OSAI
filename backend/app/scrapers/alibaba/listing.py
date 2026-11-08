"""Reading an Alibaba wholesaler listing page.

The page embeds its whole result set as a JSON object assigned to
`window._PAGE_DATA_`. That is the same data the page's own components render,
so it survives layout changes that would break a markup scraper. BeautifulSoup
reads the rendered product cards only if the JSON is missing.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from . import selectors as S
from .urls import absolute_url

_CHALLENGE_RES = [re.compile(pattern, re.I) for pattern in S.CHALLENGE_PATTERNS]
_DETAIL_ID_RE = re.compile(r"/product-detail/[^\"'\s?#]*?_(\d{6,})\.html", re.I)


@dataclass
class ListingPage:
    """What one listing page yielded."""

    #: Raw offer objects keyed by product id.
    offers: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    #: True when the offers came from the embedded JSON, False for the markup
    #: fallback (which carries far less per product).
    from_page_data: bool = True
    challenged: bool = False
    challenge_marker: Optional[str] = None


def detect_challenge(html: str) -> Optional[str]:
    """The marker that identifies an anti-bot page, or None.

    Only meaningful for a page without product JSON: real listing pages mention
    "captcha" in their scripts too, so product data present always wins.
    """
    if not html or not html.strip():
        return "empty response body"
    for pattern in _CHALLENGE_RES:
        if pattern.search(html):
            return pattern.pattern
    return None


def extract_page_data(html: str) -> Optional[Dict[str, Any]]:
    """The `window._PAGE_DATA_` object, or None if absent or malformed.

    A brace-balanced JSON decode rather than a regex: the object is hundreds of
    kilobytes of nested JSON, and a regex hunting for its end matches the wrong
    closing brace sooner or later.
    """
    at = (html or "").find(S.PAGE_DATA_MARKER)
    if at == -1:
        return None
    start = html.find("{", at)
    if start == -1:
        return None
    try:
        data, _ = json.JSONDecoder().raw_decode(html[start:])
    except (json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def offers_from_page_data(page_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Every real product offer, keyed by id. Banner and promo tiles are skipped."""
    node: Any = page_data
    for key in S.OFFER_LIST_PATH:
        node = node.get(key) if isinstance(node, dict) else None
    if not isinstance(node, list):
        return {}

    offers: Dict[str, Dict[str, Any]] = {}
    for item in node:
        offer = item.get(S.OFFER_KEY) if isinstance(item, dict) else None
        if not isinstance(offer, dict):
            continue
        information = offer.get("information") if isinstance(offer.get("information"), dict) else {}
        product_id = str(offer.get("id") or information.get("id") or "").strip()
        if product_id and information.get("productUrl"):
            offers.setdefault(product_id, offer)
    return offers


def offers_from_markup(html: str) -> Dict[str, Dict[str, Any]]:
    """Minimal offers read from rendered product cards: id, title, link, image, price text.

    Shaped like the JSON offers so the rest of the scraper handles both alike.
    Supplier credentials, tiers and specs are simply absent here.
    """
    soup = BeautifulSoup(html or "", "lxml")
    offers: Dict[str, Dict[str, Any]] = {}

    for anchor in soup.select('a[href*="/product-detail/"]'):
        href = absolute_url(anchor.get("href"))
        match = _DETAIL_ID_RE.search(href or "")
        if not href or not match or match.group(1) in offers:
            continue

        card = anchor
        for _ in range(5):
            parent = card.parent
            if parent is None or parent.name in (None, "[document]", "body"):
                break
            card = parent
            classes = " ".join(card.get("class") or [])
            if any(hint in classes for hint in ("card", "offer", "gallery", "item")):
                break

        title = (anchor.get("title") or anchor.get_text(" ", strip=True) or "").strip()
        if len(title) < 10:
            heading = card.select_one("h2, h3, [class*='title']")
            title = heading.get_text(" ", strip=True) if heading else ""
        if not title:
            continue

        image = card.select_one("img")
        image_url = None
        if image is not None:
            for attribute in ("data-src", "src", "data-image"):
                if image.get(attribute):
                    image_url = image.get(attribute)
                    break
        price_node = card.select_one("[class*='price']")

        offers[match.group(1)] = {
            "id": match.group(1),
            "information": {"enPureTitle": title, "productUrl": href},
            "image": {"bigImage": image_url},
            "tradePrice": {"price": price_node.get_text(" ", strip=True) if price_node else None},
        }
    return offers


def parse_listing(html: str) -> ListingPage:
    """Offers from a listing page, JSON first, markup second."""
    page_data = extract_page_data(html)
    if page_data is not None:
        return ListingPage(offers=offers_from_page_data(page_data), from_page_data=True)

    marker = detect_challenge(html)
    if marker:
        return ListingPage(from_page_data=False, challenged=True, challenge_marker=marker)

    return ListingPage(offers=offers_from_markup(html), from_page_data=False)
