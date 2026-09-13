"""The contract every platform scraper implements.

One folder per platform under ``app/scrapers/`` (``daraz/`` today), each
exposing a single :class:`ProductScraper`. Nothing outside a platform's own
folder may contain platform-specific knowledge, so adding a marketplace never
means touching the pipeline: write the scraper, register it, done.

Scrapers are deliberately **synchronous**. Playwright's sync API refuses to run
inside an event loop, so the Scout agent calls them through ``asyncio.to_thread``
rather than making every implementation carry an async wrapper it does not need.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

#: The two slots in a comparison. The scraper records which one it filled so
#: downstream stages can line the two products up without guessing.
OWN = "own"
COMPETITOR = "competitor"


class ScraperError(Exception):
    """A product page could not be scraped by any available method.

    The message is surfaced to the user, so implementations should say what
    failed and what the user can do about it.
    """


@dataclass
class ScrapedProductRecord:
    """One scraped listing, in a shape no part of the pipeline has to special-case.

    ``text_fields`` is what gets chunked and embedded; ``metadata`` is what gets
    compared field by field. Keeping them apart is what lets a metadata-only
    comparison run without touching the vector store at all.
    """

    role: str                                   # OWN | COMPETITOR
    platform: str                               # "daraz" | "alibaba"
    url: str
    product_name: str
    text_fields: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    method: str = "unknown"                     # "bs4" | "playwright" | "bs4+playwright"
    warnings: list[str] = field(default_factory=list)
    #: Product photos, main image first: ``{"url", "position", "source"}``
    #: with 1-based positions. URLs point at the platform's own CDN.
    images: list[dict[str, Any]] = field(default_factory=list)
    #: Quantity price breaks, lowest quantity first: ``{"min_quantity",
    #: "max_quantity" (None = open-ended), "price", "currency", "unit"}``.
    #: Empty for platforms that sell at a single price (Daraz).
    price_tiers: list[dict[str, Any]] = field(default_factory=list)
    #: The selling business's public trust profile, for platforms that publish
    #: one (Alibaba). Never contains contact details.
    supplier: dict[str, Any] | None = None

    @property
    def excerpt(self) -> str:
        """A short human-readable summary for the sources list in the UI."""
        description = (self.text_fields.get("description") or "").strip()
        if description:
            return description[:400]
        return (self.text_fields.get("title") or self.product_name)[:400]


@dataclass
class ScrapedDocument:
    """One thing a source scraper collected: a crawled page, or a social post.

    ``text_fields`` is what stage 3 chunks and embeds, one set of chunks per
    field, exactly as a product listing's fields are handled. ``metadata`` is
    the structured copy that becomes a row in the platform's detail table, and
    ``children`` carries rows that hang off that one (a post's media and
    comments), keyed by what they are.
    """

    url: str
    title: str
    text_fields: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    excerpt: str = ""
    children: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


@dataclass
class ScrapedSourceRecord:
    """Everything one submitted link yielded.

    A website link yields one document per crawled page; an Instagram profile
    link yields one per post. Either way the pipeline sees the same shape, so
    stage 2 stores both without special-casing.
    """

    role: str                                   # OWN | COMPETITOR
    kind: str                                   # "website" | "instagram"
    url: str                                    # the link the user submitted
    title: str
    documents: list[ScrapedDocument] = field(default_factory=list)
    method: str = "unknown"
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PlatformInfo:
    """What the frontend needs to render a platform in the picker."""

    platform: str
    label: str
    url_hint: str
    url_example: str


class ProductScraper(abc.ABC):
    """A scraper for one e-commerce platform."""

    #: Stable machine key. Matches the value stored in the database and sent by
    #: the frontend, so it must never change once shipped.
    platform: str = ""
    #: Shown in the platform dropdown.
    label: str = ""
    #: Placeholder/help text for the URL inputs.
    url_hint: str = ""
    url_example: str = ""

    @classmethod
    def info(cls) -> PlatformInfo:
        return PlatformInfo(
            platform=cls.platform,
            label=cls.label,
            url_hint=cls.url_hint,
            url_example=cls.url_example,
        )

    @abc.abstractmethod
    def canonical_url(self, url: str) -> str:
        """Strip tracking noise so the same listing always yields the same URL."""

    @abc.abstractmethod
    def validate_url(self, url: str) -> None:
        """Rejects a URL that this platform cannot scrape.

        Called at intake so a wrong link is caught on the form rather than
        eight minutes into a pipeline run. Raises :class:`ScraperError`.
        """

    @abc.abstractmethod
    def scrape(self, url: str, role: str) -> ScrapedProductRecord:
        """Scrape one product page. Raises :class:`ScraperError` on failure."""

    def comparison_parameters(self) -> list[dict[str, Any]]:
        """The comparison groups this platform's metadata supports.

        Empty means "no structured comparison", in which case the pipeline
        falls back to semantic evidence alone.
        """
        return []

    def build_metrics(
        self, own: dict[str, Any], competitor: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Side-by-side metric groups for two scraped products of this platform."""
        return []


class SourceScraper(abc.ABC):
    """A scraper for a comparison whose input is a site or a social profile.

    The sibling of :class:`ProductScraper`, for the two comparison types whose
    unit is not a product listing. It is deliberately a separate contract: a
    website has no price, no rating and no canonical listing identity, so
    forcing both through one interface would mean half of it returning None.

    The same rules hold: synchronous, self-contained in its own folder, and
    unaware of how anything is stored.
    """

    #: Stable machine key: the comparison type or platform it serves.
    kind: str = ""
    label: str = ""
    url_hint: str = ""
    url_example: str = ""
    #: What each collected document is recorded as in ``scraped_sources.kind``.
    source_kind: str = "landing_page"
    #: The text fields it produces, each embedded as its own set of chunks.
    text_field_types: tuple[str, ...] = ()

    @classmethod
    def is_available(cls) -> bool:
        """False when the scraper cannot run at all, e.g. a missing API token.

        Checked at intake so the user is told on the form rather than by a
        failed run.
        """
        return True

    @classmethod
    def unavailable_reason(cls) -> str:
        return f"{cls.label} scraping is not configured on this server."

    def canonical_url(self, url: str) -> str:
        """Strip tracking noise so the same link always yields the same key."""
        return (url or "").strip()

    @abc.abstractmethod
    def validate_url(self, url: str) -> None:
        """Rejects a link this scraper cannot read. Raises :class:`ScraperError`."""

    @abc.abstractmethod
    def scrape(self, url: str, role: str) -> ScrapedSourceRecord:
        """Collects everything behind one link. Raises :class:`ScraperError`."""

    def aggregate(self, documents: list[dict[str, Any]]) -> dict[str, Any]:
        """One side's stored documents, reduced to the figures a comparison reads.

        A product comparison has one row per side already; a site has many
        pages and a profile many posts, so they are summarised here. Reading it
        back from storage rather than keeping it from the scrape is deliberate:
        re-scoring never needs a re-crawl.
        """
        return {}

    def comparison_parameters(self) -> list[dict[str, Any]]:
        """The comparison groups this kind's figures support.

        Empty means "no structured comparison", in which case the screen shows
        what was collected and nothing is scored.
        """
        return []

    def build_metrics(
        self, own: dict[str, Any], competitor: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Side-by-side metric groups for two aggregated sides."""
        return []
