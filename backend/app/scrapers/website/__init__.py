"""Website scraper.

Everything website-specific lives in this folder and nowhere else:

    crawler.py    walks one site, breadth first, within a page and depth budget
    fetcher.py    one page: HTTP first, headless browser for a JavaScript shell
    cleaner.py    HTML -> title, description, headings, links, readable text
    selectors.py  every tag, selector, extension and marker the cleaner uses

The crawling and cleaning logic came from a standalone website scraper and is
unchanged; only its settings and storage were repointed at this project. This
module is the thin adapter presenting it through the platform-neutral
:class:`SourceScraper` contract, the same way the Daraz and Alibaba scrapers
are presented through :class:`ProductScraper`.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlsplit

from app.scrapers.base import ScrapedDocument, ScrapedSourceRecord, ScraperError, SourceScraper
from app.scrapers.website import metrics
from app.scrapers.website.cleaner import normalise_url
from app.scrapers.website.crawler import CrawledPage, WebsiteCrawler
from app.scrapers.website.safety import UnsafeUrl, require_public_host
from app.scrapers.website.signals import site_probes

logger = logging.getLogger("optistratix.scrapers.website")

#: Each page contributes these, chunked and embedded separately so retrieval
#: can be scoped to, say, headings alone.
TEXT_FIELD_TYPES = ["page_text", "headings", "meta"]


class WebsiteSourceScraper(SourceScraper):
    kind = "website"
    label = "Website"
    url_hint = "A public web page, usually the home page"
    url_example = "https://yourbrand.com"
    #: Every crawled page is recorded as a landing page in ``scraped_sources``.
    source_kind = "landing_page"
    text_field_types = tuple(TEXT_FIELD_TYPES)

    def canonical_url(self, url: str) -> str:
        try:
            return normalise_url(url)
        except Exception:  # noqa: BLE001 - a malformed link is validate_url's problem
            return (url or "").strip()

    def validate_url(self, url: str) -> None:
        """Shape check only: intake validation has to be instant.

        Whether the site actually answers is stage 2's problem, and is reported
        there in the crawler's own words.
        """
        value = (url or "").strip()
        if not value:
            raise ScraperError("Website URL is empty.")
        parts = urlsplit(value)
        if parts.scheme not in ("http", "https"):
            raise ScraperError(
                f"Invalid URL '{value[:80]}': must start with http:// or https://"
            )
        host = (parts.hostname or "").lower()
        if not host or "." not in host:
            raise ScraperError(
                f"'{value[:80]}' is not a website address. Enter a full link, e.g. "
                "https://yourbrand.com"
            )

        # An internal address is refused on the form as well as at fetch time:
        # the scraper runs on a server that can reach things the user cannot.
        try:
            require_public_host(value)
        except UnsafeUrl as exc:
            raise ScraperError(str(exc)) from exc

    def scrape(self, url: str, role: str) -> ScrapedSourceRecord:
        """Crawls one site and returns a document per page it could read."""
        self.validate_url(url)
        result = WebsiteCrawler().crawl(url)

        if not result.pages:
            reason = result.failures[0]["error"] if result.failures else "no readable pages"
            raise ScraperError(
                f"Nothing could be read from {url} ({reason}). Check the link opens in a "
                "browser, and that the site is publicly reachable."
            )

        warnings = [
            f"{failure['url']}: {failure['error']}" for failure in result.failures[:6]
        ]
        if len(result.failures) > 6:
            warnings.append(f"{len(result.failures) - 6} further pages could not be read.")

        # robots.txt and the sitemap belong to the site, not to any one page,
        # so they are read once and kept on the page the user submitted.
        result.pages[0].page.signals.update(site_probes(result.root_url))

        documents = [self._document(page) for page in result.pages]
        root = documents[0]

        return ScrapedSourceRecord(
            role=role,
            kind=self.kind,
            url=result.root_url,
            title=root.title or urlsplit(result.root_url).hostname or result.root_url,
            documents=documents,
            method="+".join(sorted(result.renderers)) or "unknown",
            warnings=warnings,
        )

    @staticmethod
    def _document(crawled: CrawledPage) -> ScrapedDocument:
        page = crawled.page
        headings = "\n".join(heading["text"] for heading in page.headings)
        meta = "\n".join(part for part in (page.title, page.meta_description) if part)

        return ScrapedDocument(
            url=page.page_url,
            title=page.title or page.page_url,
            excerpt=(page.meta_description or page.cleaned_text)[:400],
            text_fields={
                "page_text": page.cleaned_text,
                "headings": headings or "No headings on this page.",
                "meta": meta or "No title or description on this page.",
            },
            metadata={
                "page_url": page.page_url,
                "canonical_url": page.canonical_url,
                "status_code": crawled.status_code,
                "title": page.title or None,
                "meta_description": page.meta_description or None,
                "headings": page.headings,
                "links": page.links,
                "cleaned_text": page.cleaned_text,
                "content_hash": page.content_hash,
                "renderer": crawled.renderer,
                "word_count": page.word_count,
                "depth": crawled.depth,
                "is_root": crawled.is_root,
                "heading_count": len(page.headings),
                "link_count": len(page.links),
                # The checkable facts the A-F parameters are derived from.
                "signals": dict(page.signals),
            },
            # Stored in website_page_images, one row each, the same way a
            # listing's photos and a post's media are.
            children={"images": list(page.images)},
        )

    def aggregate(self, documents: list[dict[str, Any]]) -> dict[str, Any]:
        """One site's crawled pages, reduced to the figures A-F compare."""
        return metrics.aggregate(documents)

    def comparison_parameters(self) -> list[dict[str, Any]]:
        return metrics.PARAMETERS

    def build_metrics(
        self, own: dict[str, Any], competitor: dict[str, Any]
    ) -> list[dict[str, Any]]:
        return metrics.compare_all(own, competitor)


__all__ = ["WebsiteSourceScraper", "TEXT_FIELD_TYPES", "metrics"]
