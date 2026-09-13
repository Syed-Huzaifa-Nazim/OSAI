"""Turning one fetched HTML page into readable, storable content.

Pure: HTML in, :class:`CleanPage` out. No network and no database, so it is
exercised directly by tests against saved markup.

Ported from the standalone website scraper; the extraction rules themselves are
unchanged and live in selectors.py.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup, Comment

from . import selectors as S
from .images import collect as collect_images
from .signals import collect as collect_signals

_WHITESPACE_RE = re.compile(r"\s+")
_SLASHES_RE = re.compile(r"/+")


@dataclass
class CleanPage:
    """One page, reduced to what is worth storing."""

    page_url: str
    canonical_url: str | None
    title: str
    meta_description: str
    headings: list[dict[str, str]] = field(default_factory=list)
    links: list[dict[str, str]] = field(default_factory=list)
    cleaned_text: str = ""
    content_hash: str = ""
    #: The checkable facts behind the comparison parameters. See signals.py.
    signals: dict[str, Any] = field(default_factory=dict)
    #: The page's own marketing images, best first. See images.py.
    images: list[dict[str, Any]] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        return len(self.cleaned_text.split())


def normalise_url(url: str) -> str:
    """One spelling per page, so the same page is never crawled twice.

    Lower-cases the host, drops the default port, collapses repeated slashes,
    removes a trailing slash and discards the fragment. The query string is
    kept: on many sites it selects the content.
    """
    parts = urlsplit((url or "").strip())
    scheme = parts.scheme.lower() or "https"
    host = (parts.hostname or "").lower()
    netloc = host
    if parts.port and not ((scheme == "http" and parts.port == 80) or (scheme == "https" and parts.port == 443)):
        netloc = f"{host}:{parts.port}"
    path = _SLASHES_RE.sub("/", parts.path or "/")
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def clean_whitespace(value: str) -> str:
    """Collapses runs of whitespace but keeps line structure."""
    lines = [_WHITESPACE_RE.sub(" ", line).strip() for line in (value or "").splitlines()]
    return "\n".join(line for line in lines if line)


def clean_html(page_url: str, html: str) -> CleanPage:
    """Title, description, headings, links and body text from one page."""
    soup = BeautifulSoup(html or "", "lxml")

    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Read first: most of what the comparison measures -- scripts, nav, forms,
    # the footer's legal links -- lives in the parts stripped below. The hero
    # image is in the header, which is stripped too, so images go here as well.
    signals = collect_signals(soup, page_url)
    images = collect_images(soup, page_url)

    canonical = soup.find("link", rel=lambda value: value and "canonical" in value)
    canonical_url = (
        normalise_url(urljoin(page_url, canonical["href"]))
        if canonical and canonical.get("href")
        else None
    )

    title = clean_whitespace(soup.title.get_text(" ", strip=True)) if soup.title else ""
    description_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    meta_description = (
        clean_whitespace(str(description_tag.get("content", ""))) if description_tag else ""
    )

    headings: list[dict[str, str]] = []
    for tag in soup.find_all(S.HEADING_TAGS):
        text = clean_whitespace(tag.get_text(" ", strip=True))
        if text:
            headings.append({"level": tag.name, "text": text})

    # Collected before the page is stripped: navigation is exactly where a
    # crawler finds the rest of the site, even though it is not worth reading.
    links: list[dict[str, str]] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        absolute = normalise_url(urljoin(page_url, anchor["href"]))
        if absolute in seen:
            continue
        seen.add(absolute)
        links.append({
            "url": absolute,
            "text": clean_whitespace(anchor.get_text(" ", strip=True))[: S.MAX_LINK_TEXT],
        })

    for name in S.REMOVE_TAGS:
        for tag in soup.find_all(name):
            tag.decompose()
    for selector in S.BOILERPLATE_SELECTORS:
        for node in soup.select(selector):
            node.decompose()

    main = _main_content(soup)
    text = clean_whitespace(main.get_text("\n", strip=True))

    return CleanPage(
        page_url=normalise_url(page_url),
        canonical_url=canonical_url,
        title=title,
        meta_description=meta_description,
        headings=headings,
        links=links,
        cleaned_text=text,
        content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        signals=signals,
        images=images,
    )


def _main_content(soup: Any) -> Any:
    """The page's own content, when it says where that is."""
    main = soup.find("main") or soup.find(attrs={"role": "main"})
    if main is None:
        articles = soup.find_all("article")
        if len(articles) == 1:
            main = articles[0]
    return main if main is not None else (soup.body or soup)


def probable_javascript_shell(html: str, text: str, min_length: int) -> bool:
    """True when a page arrived as an empty frame for JavaScript to fill.

    Deciding this on text length alone would send every genuinely short page to
    the browser, so a shell marker (or a page that is almost all script) has to
    be present as well.
    """
    lower = (html or "").lower()
    if len(text) >= min_length:
        return False
    return any(marker in lower for marker in S.JAVASCRIPT_SHELL_MARKERS) or (
        lower.count("<script") >= S.JAVASCRIPT_SHELL_SCRIPT_COUNT
    )
