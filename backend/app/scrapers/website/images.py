"""The pictures a page actually shows.

Read from the markup **before** the cleaner strips it, for the same reason the
signals are: a hero image almost always lives in the header, which is exactly
what gets thrown away. Pure -- soup in, rows out, no network.

Nothing is downloaded or re-hosted. The page's own URL is stored, the same way
a marketplace listing's photos and an Instagram post's media are, so one
approach covers every scraper.

What is deliberately left out: icons, logos, sprites, flags, spacers, tracking
pixels and SVGs. A comparison is judging how a site presents itself, and a
grid full of chevrons and favicons says nothing about that. The rules live in
selectors.py.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from . import selectors as S

_INT_RE = re.compile(r"(\d+)")
#: "photo-640.jpg 640w, photo-1280.jpg 1280w" -> the widest candidate.
_SRCSET_ENTRY_RE = re.compile(r"\s*(\S+)(?:\s+([\d.]+)[wx])?\s*")


def collect(soup: Any, page_url: str) -> list[dict[str, Any]]:
    """Every image worth keeping from one page, most representative first.

    Order is the point: the social preview image first (a site chooses that one
    deliberately), then the hero, then body content in document order. Position
    1 is what the results screen shows as the page's picture.
    """
    found: list[dict[str, Any]] = []
    seen: set[str] = set()

    social = soup.find("meta", attrs={"property": re.compile("^og:image$", re.I)}) or soup.find(
        "meta", attrs={"name": re.compile("^twitter:image$", re.I)}
    )
    if social and social.get("content"):
        _add(found, seen, page_url, str(social["content"]), "og_image", "", None, None)

    hero_nodes: list[Any] = []
    for selector in S.HERO_CONTAINERS:
        try:
            containers = soup.select(selector)
        except Exception:  # noqa: BLE001 - a malformed selector must not fail a crawl
            continue
        for container in containers:
            hero_nodes.extend(container.find_all("img"))

    # Hero nodes first, so an image that is both claims the better label. The
    # URL set makes the second pass skip whatever the first already took.
    for node, source in [(node, "hero") for node in hero_nodes] + [
        (node, "content") for node in soup.find_all("img")
    ]:
        if len(found) >= S.MAX_IMAGES_PER_PAGE:
            break
        raw = _source_url(node)
        if not raw:
            continue
        _add(
            found,
            seen,
            page_url,
            raw,
            source,
            str(node.get("alt") or ""),
            _dimension(node, "width"),
            _dimension(node, "height"),
        )

    images = found[: S.MAX_IMAGES_PER_PAGE]
    for index, image in enumerate(images):
        # Mirrors the storage rule that the primary image is the first one.
        image["is_primary"] = index == 0
    return images


def _add(
    found: list[dict[str, Any]],
    seen: set[str],
    page_url: str,
    raw: str,
    source: str,
    alt: str,
    width: int | None,
    height: int | None,
) -> None:
    url = _absolute(page_url, raw)
    if not url or url in seen or not _is_content_image(url, width, height):
        return
    seen.add(url)
    found.append({
        "image_url": url[:2000],
        "source": source,
        "alt_text": (alt.strip()[:300] or None),
        "width": width,
        "height": height,
    })


def _source_url(node: Any) -> str:
    """The first attribute that actually carries a source."""
    for attribute in S.IMAGE_SRC_ATTRIBUTES:
        value = str(node.get(attribute) or "").strip()
        if not value:
            continue
        if attribute.endswith("srcset"):
            value = _largest_in_srcset(value)
        if value:
            return value
    return ""


def _largest_in_srcset(value: str) -> str:
    """The widest candidate a responsive image offers."""
    best_url, best_width = "", -1.0
    for candidate in value.split(","):
        match = _SRCSET_ENTRY_RE.fullmatch(candidate)
        if not match or not match.group(1):
            continue
        width = float(match.group(2)) if match.group(2) else 0.0
        if width >= best_width:
            best_url, best_width = match.group(1), width
    return best_url


def _dimension(node: Any, attribute: str) -> int | None:
    """A declared width/height, from the attribute or an inline style."""
    match = _INT_RE.search(str(node.get(attribute) or ""))
    if match:
        return int(match.group(1))
    style = str(node.get("style") or "")
    match = re.search(rf"{attribute}\s*:\s*(\d+)px", style, re.I)
    return int(match.group(1)) if match else None


def _absolute(page_url: str, raw: str) -> str:
    value = raw.strip()
    if not value or value.lower().startswith("data:"):
        return ""
    try:
        absolute = urljoin(page_url, value)
    except ValueError:
        return ""
    return absolute if absolute.lower().startswith(("http://", "https://")) else ""


def _is_content_image(url: str, width: int | None, height: int | None) -> bool:
    """False for chrome: icons, logos, spacers and tracking pixels."""
    lowered = url.lower().split("?")[0]
    if lowered.endswith(S.IMAGE_SKIP_EXTENSIONS):
        return False
    if any(fragment in lowered for fragment in S.IMAGE_SKIP_URL_FRAGMENTS):
        return False
    # Only a *declared* dimension can disqualify an image: most sites declare
    # none at all, and assuming those are tiny would empty the gallery.
    for dimension in (width, height):
        if dimension is not None and dimension < S.MIN_IMAGE_DIMENSION:
            return False
    return True


__all__ = ["collect"]
