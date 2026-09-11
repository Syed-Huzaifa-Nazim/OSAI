"""Product image extraction for Daraz listings.

Runs inside the same extraction pass as price, specs and reviews, over the
same HTML the scraper already fetched -- no extra page load. Like the rest of
the scraper it reads the most stable source first and falls back:

    1. the gallery in the inline module-data blob   (full-resolution originals)
    2. JSON-LD structured data                      (full-resolution originals)
    3. gallery <img> tags on the page               (often resized thumbnails)
    4. the og:image meta tag                        (last resort, one image)

Every URL is normalised to the original file: protocol-relative links get a
scheme, Daraz's resize suffix is stripped, and lazy-loading placeholders are
ignored in favour of the attribute holding the real image. The same photo is
served from several CDN hosts, so duplicates are recognised by filename.

Nothing in here raises for a page that is merely missing images. A listing
with no photos yields an empty list, and the caller records a warning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from . import selectors as S
from .utils import deep_get

_RESIZE_RE = re.compile(S.IMAGE_RESIZE_SUFFIX, flags=re.I)
_IMAGE_EXTENSION_RE = re.compile(r"\.(?:jpe?g|png|webp|gif)$", flags=re.I)

#: Where an image was found, from most to least trustworthy.
SOURCE_GALLERY = "gallery"
SOURCE_STRUCTURED_DATA = "structured_data"
SOURCE_PAGE = "page"
SOURCE_OG_IMAGE = "og_image"


@dataclass
class ProductImage:
    url: str
    source: str


def extract_product_images(
    soup: BeautifulSoup,
    module: Dict[str, Any],
    jsonld: Dict[str, Any],
) -> List[ProductImage]:
    """Every distinct product photo on the listing, main image first."""
    collected = _Collector()

    for path in S.IMAGE_GALLERY_PATHS:
        collected.add_all(_gallery_urls(deep_get(module, path)), SOURCE_GALLERY)
    collected.add_all(_structured_data_urls(jsonld.get("image") if jsonld else None), SOURCE_STRUCTURED_DATA)

    # Page <img> tags only when the structured sources had nothing. The CSS
    # selectors are broad enough to catch a video poster or a badge, which is
    # harmless as a fallback but would pollute a gallery that is already known.
    if not collected.images:
        collected.add_all(_page_image_urls(soup), SOURCE_PAGE)

    # og:image is a single promotional shot; only use it if nothing else exists.
    if not collected.images:
        og = soup.select_one('meta[property="og:image"]')
        collected.add_all([og.get("content")] if og else [], SOURCE_OG_IMAGE)

    return collected.images


def count_videos(module: Dict[str, Any]) -> int:
    """Gallery entries that are not pictures (product videos)."""
    total = 0
    for path in S.IMAGE_GALLERY_PATHS:
        for entry in _gallery_entries(deep_get(module, path)):
            if str(entry.get("type", "")).lower() not in S.IMAGE_GALLERY_TYPES:
                total += 1
    return total


def normalise_image_url(raw: Any) -> Optional[str]:
    """The full-resolution, absolute URL for an image reference, or None.

    None means "not a product image": empty, a data URI, a spacer gif, or not
    a link to an image file at all.
    """
    if not isinstance(raw, str):
        return None
    url = raw.strip().strip("'\"")
    if not url:
        return None
    lowered = url.lower()
    if any(hint in lowered for hint in S.IMAGE_PLACEHOLDER_HINTS):
        return None

    if url.startswith("//"):
        url = "https:" + url
    if not url.startswith(("http://", "https://")):
        return None

    # Drop any query/fragment before inspecting the filename; image CDNs do not
    # need them and they defeat de-duplication.
    parsed = urlparse(url)
    path = _RESIZE_RE.sub(r"\1", parsed.path)
    if not _IMAGE_EXTENSION_RE.search(path):
        return None
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def image_identity(url: str) -> str:
    """What makes two URLs the same photo.

    Daraz serves one file from several hosts and path prefixes
    (static-01.daraz.pk/p/abc.jpg, img.drz.lazcdn.com/static/pk/p/abc.jpg), but
    the filename is a content hash and stays the same.
    """
    return urlparse(url).path.rsplit("/", 1)[-1].lower()


# ---------------------------------------------------------------- sources


def _gallery_entries(node: Any) -> Iterable[Dict[str, Any]]:
    """Gallery entries in display order: the listing's own ("0") first, then
    each SKU's, so variant photos follow the main gallery."""
    if isinstance(node, list):
        groups = [node]
    elif isinstance(node, dict):
        keys = sorted(node, key=lambda key: (str(key) != "0", str(key)))
        groups = [node[key] for key in keys]
    else:
        return []
    return [entry for group in groups if isinstance(group, list) for entry in group if isinstance(entry, dict)]


def _gallery_urls(node: Any) -> List[str]:
    urls: List[str] = []
    for entry in _gallery_entries(node):
        if str(entry.get("type", "img")).lower() not in S.IMAGE_GALLERY_TYPES:
            continue
        for key in S.IMAGE_GALLERY_ENTRY_KEYS:
            if entry.get(key):
                urls.append(entry[key])
                break
    return urls


def _structured_data_urls(node: Any) -> List[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        return [item if isinstance(item, str) else (item or {}).get("url") for item in node]
    if isinstance(node, dict):
        return [node.get("url") or node.get("contentUrl")]
    return []


def _page_image_urls(soup: BeautifulSoup) -> List[str]:
    urls: List[str] = []
    for selector in S.CSS.get("images", []):
        try:
            nodes = soup.select(selector)
        except Exception:
            continue
        for node in nodes:
            best = _best_img_reference(node)
            if best:
                urls.append(best)
    return urls


def _best_img_reference(node: Any) -> Optional[str]:
    """The attribute on an <img> that actually holds the photo.

    A lazy image's `src` is typically a placeholder until JavaScript swaps in
    the real URL from a data attribute, so data attributes are read first.
    """
    for attribute in S.IMAGE_LAZY_ATTRIBUTES:
        if normalise_image_url(node.get(attribute)):
            return node.get(attribute)
    for attribute in S.IMAGE_SRCSET_ATTRIBUTES:
        candidate = _largest_srcset_entry(node.get(attribute))
        if normalise_image_url(candidate):
            return candidate
    src = node.get("src")
    return src if normalise_image_url(src) else None


def _largest_srcset_entry(srcset: Any) -> Optional[str]:
    """'a.jpg 120w, b.jpg 720w' -> 'b.jpg'."""
    if not isinstance(srcset, str) or not srcset.strip():
        return None
    best_url, best_width = None, -1
    for part in srcset.split(","):
        pieces = part.strip().split()
        if not pieces:
            continue
        width = 0
        if len(pieces) > 1:
            match = re.match(r"(\d+(?:\.\d+)?)", pieces[1])
            width = int(float(match.group(1))) if match else 0
        if width >= best_width:
            best_url, best_width = pieces[0], width
    return best_url


class _Collector:
    """Ordered, de-duplicated, capped list of images."""

    def __init__(self) -> None:
        self.images: List[ProductImage] = []
        self._seen: set = set()

    def add_all(self, raw_urls: Iterable[Any], source: str) -> None:
        for raw in raw_urls:
            if len(self.images) >= S.IMAGE_MAX_PER_PRODUCT:
                return
            url = normalise_image_url(raw)
            if not url:
                continue
            identity = image_identity(url)
            if identity in self._seen:
                continue
            self._seen.add(identity)
            self.images.append(ProductImage(url=url, source=source))
