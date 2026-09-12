"""Reading Alibaba product links.

A pasted link is never fetched (product pages are CAPTCHA-protected); it is
read for two things: the product id, which is how the listing record is matched,
and the title words in its slug, which are what the listing is searched with.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import unquote, urlparse

from . import selectors as S

_PRODUCT_PATTERNS = [re.compile(pattern, re.I) for pattern in S.PRODUCT_URL_PATTERNS]


class InvalidAlibabaUrl(ValueError):
    """The link is not an Alibaba product page. The message is user-facing."""


@dataclass(frozen=True)
class ProductLink:
    product_id: str
    #: Title words from the link, lower-cased and hyphen-joined, for searching.
    #: Empty when the link carries no title (a bare mobile link).
    slug: str
    #: The same words with their original capitalisation, for the display link.
    title_slug: str = ""

    @property
    def canonical_url(self) -> str:
        return S.CANONICAL_PRODUCT_URL.format(
            slug=self.title_slug or self.slug or "product", product_id=self.product_id
        )


def parse_product_link(raw_url: str) -> ProductLink:
    """The product id and title slug from a desktop or mobile product link."""
    url = (raw_url or "").strip()
    if not url:
        raise InvalidAlibabaUrl("Product URL is empty.")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise InvalidAlibabaUrl(f"Invalid URL '{url[:80]}': must start with http:// or https://")

    host = (parsed.hostname or "").lower()
    if not host:
        raise InvalidAlibabaUrl(f"Invalid URL '{url[:80]}': no host found.")
    if host != S.ALLOWED_HOST_SUFFIX and not host.endswith("." + S.ALLOWED_HOST_SUFFIX):
        raise InvalidAlibabaUrl(
            f"'{host}' is not an Alibaba domain. This option only supports Alibaba product links "
            "(e.g. https://www.alibaba.com/product-detail/...)."
        )

    path = unquote(parsed.path or "/")
    for pattern in _PRODUCT_PATTERNS:
        match = pattern.match(path)
        if match:
            raw_slug = match.group("slug") or ""
            return ProductLink(
                product_id=match.group("id"),
                slug=normalise_slug(raw_slug),
                title_slug="-".join(re.findall(r"[A-Za-z0-9]+", raw_slug)),
            )

    raise InvalidAlibabaUrl(
        "That Alibaba link is not a single product page. Paste a product link that looks like "
        "https://www.alibaba.com/product-detail/Product-Name_1601234567890.html"
    )


def normalise_slug(slug: str) -> str:
    """'Mini-Wireless-Mouse_Ergonomic' -> 'mini-wireless-mouse-ergonomic'."""
    words = re.findall(r"[a-z0-9]+", (slug or "").lower())
    return "-".join(words)


def search_slugs(slug: str) -> List[str]:
    """Listing search terms to try for a product, most specific first.

    The link's own slug comes first -- it is the product title Alibaba itself
    wrote into the URL. Shorter variants drop generic words and trim to the
    leading words, which usually name the product type.
    """
    words = [word for word in (slug or "").split("-") if word]
    if not words:
        return []

    candidates: List[str] = []

    def add(parts: List[str]) -> None:
        candidate = "-".join(parts)
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    add(words[: S.SEARCH_WORD_LIMITS[0]])
    meaningful = [word for word in words if word not in S.SEARCH_STOPWORDS] or words
    for limit in S.SEARCH_WORD_LIMITS[1:]:
        if len(meaningful) >= 2:
            add(meaningful[:limit])
    return candidates


def listing_url(search_slug: str) -> str:
    """The permitted listing URL for a search term. Never carries a query string."""
    return S.LISTING_URL_TEMPLATE.format(slug=search_slug)


def absolute_url(value: Optional[str]) -> Optional[str]:
    """Alibaba emits protocol-relative URLs; make them absolute."""
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    if value.startswith("//"):
        return "https:" + value
    if value.startswith(("http://", "https://")):
        return value
    if value.startswith("/"):
        return "https://www.alibaba.com" + value
    return None
