"""Scraped website pages and social posts (stage 2, website/social comparisons).

The structured copy of what the website and Instagram scrapers read, as the
scraped-data screen shows it. One row per crawled page or per post, the same
way ``EcommerceProduct`` is one row per scraped listing.

Deliberately not the whole stored row: the page's full text and its link list
stay in the database, because the screen shows a preview and the counts, and
shipping every link of every page would be a far larger payload than anything
rendered from it.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field

from app.models.common import CamelModel


class SourceRole(str, Enum):
    """Which side of the comparison a page or post belongs to."""

    OWN = "own"
    COMPETITOR = "competitor"


class PageImage(CamelModel):
    """One picture a crawled page shows. The URL is the site's own."""

    id: str
    page_id: str
    project_id: str
    #: 1-based. Position 1 is the page's most representative image.
    position: int
    image_url: str
    alt_text: str | None = None
    #: "og_image" | "hero" | "content": where on the page it was found.
    source: str = "content"
    width: int | None = None
    height: int | None = None
    is_primary: bool = False


class PostMedia(CamelModel):
    """One image or video of a post. Carousels keep their slide order."""

    id: str
    post_id: str
    project_id: str
    position: int
    media_type: str | None = None
    #: Instagram's own CDN URL. Nothing is downloaded or re-hosted.
    media_url: str


class PostComment(CamelModel):
    """One public comment collected for a post."""

    id: str
    post_id: str
    project_id: str
    position: int
    commenter_username: str | None = None
    comment_text: str = ""
    like_count: int | None = None
    posted_at: str | None = None


class ScrapedPage(CamelModel):
    """One crawled page of a website."""

    id: str
    project_id: str
    #: The scraped_sources row this page produced, for citation lookups.
    source_id: str | None = None
    #: Null for the user's own site, set for a competitor's.
    competitor_id: str | None = None
    role: SourceRole
    #: The link the user submitted; page_url is this particular page.
    submitted_url: str
    page_url: str
    canonical_url: str | None = None
    status_code: int | None = None
    title: str | None = None
    meta_description: str | None = None
    #: [{level, text}] in document order.
    headings: list[dict[str, Any]] = Field(default_factory=list)
    heading_count: int = 0
    link_count: int = 0
    word_count: int = 0
    #: The opening of the cleaned text. The full text stays in the database.
    text_preview: str = ""
    renderer: str = "http"
    #: Clicks from the submitted link; 0 is the page the user gave us.
    depth: int = 0
    is_root: bool = False
    scraped_at: str
    #: Not a column: attached from website_page_images when the page is read
    #: back, the same way a listing's photos are.
    images: list[PageImage] = Field(default_factory=list)


class ScrapedPost(CamelModel):
    """One public post on a scraped Instagram profile."""

    id: str
    project_id: str
    source_id: str | None = None
    competitor_id: str | None = None
    role: SourceRole
    submitted_url: str
    profile_url: str | None = None
    post_url: str | None = None
    #: The scraped profile's own handle, from the profile the link pointed at.
    #: This is what the screen labels the side with.
    profile_username: str | None = None
    #: Who wrote this particular post. Usually the profile owner, but a
    #: collaboration post carries the other collaborator's handle instead.
    owner_username: str | None = None
    caption: str = ""
    caption_word_count: int = 0
    hashtags: list[str] = Field(default_factory=list)
    hashtag_count: int = 0
    like_count: int | None = None
    comment_count: int | None = None
    #: likes + comments, so a ranking needs no arithmetic.
    engagement_count: int = 0
    video_view_count: int | None = None
    media_type: str | None = None
    media_url: str | None = None
    media_count: int = 0
    location_name: str | None = None
    is_sponsored: bool = False
    posted_at: str | None = None
    #: How many comments were actually collected for this post.
    collected_comment_count: int = 0
    scraped_at: str
    #: Neither is a column: both are attached when the post is read back.
    media: list[PostMedia] = Field(default_factory=list)
    comments: list[PostComment] = Field(default_factory=list)


class ScrapedDocuments(CamelModel):
    """Everything a website or social comparison collected, both sides together.

    One shape for both kinds so the screen makes a single request: whichever
    list is filled is the one the project's comparison type produced.
    """

    #: "website" | "instagram", or empty for a comparison that has neither.
    kind: str = ""
    pages: list[ScrapedPage] = Field(default_factory=list)
    posts: list[ScrapedPost] = Field(default_factory=list)
