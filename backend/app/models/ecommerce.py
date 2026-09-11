"""Scraped marketplace listings (stage 2, e-commerce comparisons).

One row per scraped product. The columns here are the fields every marketplace
has, so a second platform reuses this shape rather than getting a table of its
own; anything Daraz-specific rides along in ``raw_metadata``.

``text_fields`` is the chunkable content (title, description, specs, reviews,
...). It is kept on the row rather than only in Chroma so a re-embed never
needs a re-scrape, and so the evidence quoted in a gap can always be resolved
back to stored text.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field

from app.models.common import CamelModel


class ProductRole(str, Enum):
    """Which side of the comparison a listing fills."""

    OWN = "own"
    COMPETITOR = "competitor"


class ScrapeMethod(str, Enum):
    """How the page was actually read. Surfaced in the UI because a
    Playwright-only scrape is slower and more fragile than a plain fetch, and
    that is worth knowing when a result looks thin."""

    BS4 = "bs4"
    PLAYWRIGHT = "playwright"
    BS4_PLAYWRIGHT = "bs4+playwright"
    UNKNOWN = "unknown"


class ImageSource(str, Enum):
    """Where on the page a photo was found, most trustworthy first."""

    GALLERY = "gallery"
    STRUCTURED_DATA = "structured_data"
    PAGE = "page"
    OG_IMAGE = "og_image"


class ProductImage(CamelModel):
    """One product photo. The URL is the platform's own; nothing is re-hosted."""

    id: str
    product_id: str
    project_id: str
    #: 1-based gallery order. Position 1 is the main image.
    position: int
    url: str
    is_primary: bool = False
    source: ImageSource = ImageSource.GALLERY


class EcommerceProduct(CamelModel):
    id: str
    project_id: str
    #: Null for the user's own listing, set for a competitor's.
    competitor_id: str | None = None
    #: The scraped_sources row this product produced, for citation lookups.
    source_id: str | None = None
    platform: str
    role: ProductRole
    url: str
    product_name: str

    # --- the fields every marketplace has, promoted to real columns ---------
    brand: str | None = None
    price: float | None = None
    original_price: float | None = None
    discount_percent: float | None = None
    currency: str = "PKR"
    rating: float | None = None
    review_count: int = 0
    image_count: int = 0
    seller_name: str | None = None
    seller_rating: float | None = None
    stock_status: str | None = None
    category: str | None = None
    content_completeness_score: float | None = None

    # --- everything else ----------------------------------------------------
    #: Chunkable content, keyed by field type.
    text_fields: dict[str, str] = Field(default_factory=dict)
    #: The full scraper output, including platform-specific fields that have no
    #: column. This is what the comparison engine reads.
    raw_metadata: dict[str, Any] = Field(default_factory=dict)

    scrape_method: ScrapeMethod = ScrapeMethod.UNKNOWN
    warnings: list[str] = Field(default_factory=list)
    chunk_count: int = 0
    scraped_at: str
    #: Main image first. Not a column: attached from ecommerce_product_images
    #: when the listing is read back.
    images: list[ProductImage] = Field(default_factory=list)


class MetricRow(CamelModel):
    """One directly comparable field, rendered as a row in the comparison table."""

    field: str
    label: str
    own: str | float | int | bool | None = None
    competitor: str | float | int | bool | None = None
    unit: str | None = None
    #: "currency" | "percent" | "number" | "rating" | "bool" | "text"
    kind: str = "text"
    higher_is_better: bool | None = None
    #: "own" | "competitor" | "tie", or None when the field is descriptive or
    #: one side is missing. Never defaulted -- an unmeasured field has no winner.
    winner: str | None = None
    delta: float | None = None
    delta_label: str | None = None


class ComparisonGroup(CamelModel):
    """One parameter group (A-H for Daraz) with its rows and findings."""

    key: str
    letter: str
    label: str
    description: str
    gap_category: str
    metrics: list[MetricRow] = Field(default_factory=list)
    own_derived: dict[str, Any] = Field(default_factory=dict)
    competitor_derived: dict[str, Any] = Field(default_factory=dict)
    insights: list[str] = Field(default_factory=list)
    own_wins: int = 0
    competitor_wins: int = 0
    #: The text fields this group searches. Empty for a metadata-only group
    #: (pricing, variants), which is compared from numbers alone.
    semantic_field_types: list[str] = Field(default_factory=list)
    #: The natural-language query used to retrieve passages, if any.
    query: str | None = None

    @property
    def metadata_only(self) -> bool:
        return not self.semantic_field_types


class SemanticSnippet(CamelModel):
    """A passage retrieved from one listing's embedded text."""

    field_type: str
    text: str
    #: Cosine similarity to the group's query, 0-1. Higher is more relevant.
    score: float | None = None
    chunk_index: int = 0


class ProductSide(CamelModel):
    """One listing's half of a parameter comparison."""

    product_id: str
    role: str
    product_name: str
    url: str
    snippets: list[SemanticSnippet] = Field(default_factory=list)
    #: Parameter-specific figures that are not plain field reads, e.g. a
    #: volume-weighted credibility index for social proof.
    derived: dict[str, Any] = Field(default_factory=dict)


class ParameterComparison(CamelModel):
    """Everything the comparison page shows for one selected parameter."""

    parameter: ComparisonGroup
    metadata_only: bool
    own: ProductSide
    competitor: ProductSide


class PlatformOption(CamelModel):
    """A platform the frontend can offer in the e-commerce dropdown.

    Served from the scraper registry, so the dropdown gains a new option the
    moment a scraper is registered -- the frontend keeps no platform list.
    """

    platform: str
    label: str
    url_hint: str
    url_example: str
