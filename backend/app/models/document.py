"""Strategy documents and stage-9 content assets."""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from app.models.common import CamelModel


class DocumentFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    MARKDOWN = "markdown"


class DocumentSection(CamelModel):
    id: str
    heading: str
    body: str
    order: int


class StrategyDocument(CamelModel):
    id: str
    project_id: str
    strategy_id: str
    title: str
    content: str
    sections: list[DocumentSection] = Field(default_factory=list)
    available_formats: list[DocumentFormat] = Field(default_factory=list)
    word_count: int = 0
    generated_at: str


class AssetKind(str, Enum):
    BLOG = "blog"
    SOCIAL_POST = "social_post"
    AD_COPY = "ad_copy"
    SEO_BRIEF = "seo_brief"
    EMAIL = "email"


class AssetStatus(str, Enum):
    SUGGESTED = "suggested"
    QUEUED = "queued"
    GENERATED = "generated"
    DISMISSED = "dismissed"


class ContentSuggestion(CamelModel):
    id: str
    project_id: str
    kind: AssetKind
    title: str
    angle: str
    linked_initiative_id: str | None = None
    target_keywords: list[str] = Field(default_factory=list)
    channel: str
    estimated_effort_hours: int = Field(ge=0, le=200)
    status: AssetStatus = AssetStatus.SUGGESTED
    body: str | None = None
    created_at: str


class ContentSuggestionPatch(CamelModel):
    status: AssetStatus | None = None
    body: str | None = None
