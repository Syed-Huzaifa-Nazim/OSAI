"""Walking one site, breadth first, from the link the user submitted.

Same-host only, robots.txt respected, and bounded by a page budget and a depth
limit so a comparison cannot turn into an open-ended crawl. Collects pages and
returns them; nothing here writes to a database.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from app.core.config import settings
from . import selectors as S
from .cleaner import CleanPage, clean_html, normalise_url
from .fetcher import Fetcher

log = logging.getLogger(__name__)


@dataclass
class CrawledPage:
    page: CleanPage
    status_code: int | None
    renderer: str
    depth: int
    is_root: bool


@dataclass
class CrawlResult:
    root_url: str
    pages: list[CrawledPage] = field(default_factory=list)
    discovered: int = 0
    failures: list[dict[str, Any]] = field(default_factory=list)
    #: Pages skipped because their text was identical to one already stored.
    duplicates: int = 0

    @property
    def renderers(self) -> set[str]:
        return {page.renderer for page in self.pages}


class WebsiteCrawler:
    """One crawl of one site."""

    def __init__(
        self,
        renderer: str = "auto",
        max_pages: int | None = None,
        max_depth: int | None = None,
    ) -> None:
        self.renderer = renderer
        self.max_pages = max_pages or settings.website_max_pages
        self.max_depth = settings.website_max_depth if max_depth is None else max_depth
        self.fetcher = Fetcher()

    def crawl(self, root_url: str) -> CrawlResult:
        root = normalise_url(root_url)
        host = urlsplit(root).hostname or ""
        result = CrawlResult(root_url=root)
        robots = self._robots(root)

        queue: deque[tuple[str, int]] = deque([(root, 0)])
        queued = {root}
        visited: set[str] = set()
        # Sites routinely serve one page at several URLs (/ and /index.html).
        # Storing both would spend the page budget twice and put the same text
        # into the vector store twice, which skews every later retrieval.
        stored_hashes: set[str] = set()

        while queue and len(result.pages) < self.max_pages:
            current, depth = queue.popleft()
            current = normalise_url(current)
            if current in visited:
                continue
            visited.add(current)

            if robots is not None and not robots.can_fetch(S.USER_AGENT, current):
                result.failures.append({"url": current, "error": "Disallowed by robots.txt"})
                continue

            fetched = self.fetcher.fetch(current, self.renderer)
            if fetched.error:
                result.failures.append({"url": current, "error": fetched.error})
                continue

            page = clean_html(fetched.final_url, fetched.html)
            if not page.cleaned_text.strip():
                result.failures.append({"url": current, "error": "No readable text on the page"})
                continue

            if page.content_hash in stored_hashes:
                # Not a failure: the content is already stored under its other
                # URL, so this is a skip, not something to warn the user about.
                result.duplicates += 1
                log.debug("Skipping %s: same text as a page already stored", current)
                continue
            stored_hashes.add(page.content_hash)

            result.pages.append(
                CrawledPage(
                    page=page,
                    status_code=fetched.status_code,
                    renderer=fetched.renderer,
                    depth=depth,
                    is_root=depth == 0,
                )
            )

            if depth < self.max_depth:
                for candidate in self._followable(page, host, queued):
                    queue.append((candidate, depth + 1))
                    queued.add(candidate)

            result.discovered = len(queued)

        result.discovered = max(result.discovered, len(queued))
        return result

    @staticmethod
    def _followable(page: CleanPage, host: str, queued: set[str]) -> list[str]:
        """Links worth queueing: same host, a real page, not already seen."""
        out: list[str] = []
        for link in page.links:
            candidate = link["url"]
            parts = urlsplit(candidate)
            path = parts.path.lower()
            if (
                parts.scheme in {"http", "https"}
                and (parts.hostname or "") == host
                and candidate not in queued
                and not path.endswith(S.SKIP_EXTENSIONS)
                and not any(fragment in path for fragment in S.SKIP_PATH_FRAGMENTS)
            ):
                out.append(candidate)
        return out

    @staticmethod
    def _robots(root: str) -> RobotFileParser | None:
        """The site's robots.txt, or None when it is switched off or unreachable.

        An unreachable robots.txt imposes no restrictions, which is what the
        standard says and what the standalone scraper did.
        """
        if not settings.website_respect_robots_txt:
            return None
        parts = urlsplit(root)
        parser = RobotFileParser()
        parser.set_url(f"{parts.scheme}://{parts.netloc}/robots.txt")
        try:
            parser.read()
            return parser
        except Exception as exc:  # noqa: BLE001 - no robots.txt means no rules
            log.info("Could not read robots.txt for %s (%s); proceeding", root, exc)
            return None
