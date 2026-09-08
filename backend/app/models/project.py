"""Projects, competitors and scraped sources (stages 1-3)."""

from __future__ import annotations

from enum import Enum

from pydantic import Field, field_validator

from app.models.common import CamelModel


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETE = "complete"
    FAILED = "failed"
    ARCHIVED = "archived"


class Industry(str, Enum):
    SAAS = "saas"
    ECOMMERCE = "ecommerce"
    FINTECH = "fintech"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    HOSPITALITY = "hospitality"
    AGENCY = "agency"
    MANUFACTURING = "manufacturing"
    OTHER = "other"


class SocialPlatform(str, Enum):
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    X = "x"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"


class SocialHandle(CamelModel):
    platform: SocialPlatform
    handle: str = Field(max_length=60)


class CompetitorInput(CamelModel):
    name: str = Field(min_length=2, max_length=120)
    landing_page_url: str = Field(max_length=500)
    social_handles: list[SocialHandle] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("landing_page_url")
    @classmethod
    def must_be_http_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("Enter a full URL, including https://")
        return value


class Competitor(CompetitorInput):
    id: str
    project_id: str
    created_at: str


class ProjectCreate(CamelModel):
    """Stage 1 intake. Mirrors the zod schema the form validates against, so a
    client that skips validation still cannot write a bad row."""

    brand_name: str = Field(min_length=2, max_length=120)
    brand_website: str | None = Field(default=None, max_length=500)
    brand_description: str = Field(min_length=40, max_length=1200)
    industry: Industry
    target_audience: str = Field(min_length=20, max_length=600)
    objectives: list[str] = Field(min_length=1, max_length=6)
    competitors: list[CompetitorInput] = Field(min_length=1, max_length=5)

    @field_validator("objectives")
    @classmethod
    def objectives_not_blank(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("Add at least one objective")
        return cleaned


class Project(CamelModel):
    id: str
    owner_id: str
    brand_name: str
    brand_website: str | None = None
    brand_description: str
    industry: Industry
    target_audience: str
    objectives: list[str] = Field(default_factory=list)
    status: ProjectStatus = ProjectStatus.DRAFT
    current_stage: int = 1
    competitor_count: int = 0
    gap_count: int = 0
    is_demo: bool = False
    created_at: str
    updated_at: str


class SourceKind(str, Enum):
    LANDING_PAGE = "landing_page"
    SOCIAL_POST = "social_post"
    REVIEW = "review"
    FORUM_THREAD = "forum_thread"
    NEWS_ARTICLE = "news_article"


class SourceStatus(str, Enum):
    PENDING = "pending"
    SCRAPED = "scraped"
    EMBEDDED = "embedded"
    FAILED = "failed"


class ScrapedSource(CamelModel):
    id: str
    project_id: str
    competitor_id: str | None = None
    kind: SourceKind
    url: str
    title: str
    excerpt: str
    status: SourceStatus = SourceStatus.PENDING
    chunk_count: int = 0
    scraped_at: str
