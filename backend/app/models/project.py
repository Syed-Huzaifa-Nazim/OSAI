"""Projects, competitors and scraped sources (stages 1-3)."""

from __future__ import annotations

from enum import Enum
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator

from app.models.common import CamelModel
from app.scrapers import get_scraper, is_supported, platform_keys, source_kind_for, source_kinds


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


class ComparisonType(str, Enum):
    """What the user is comparing themselves against.

    Stage 2 branches on this to pick a data-acquisition strategy, so adding a
    kind of comparison means adding a value here and a branch in the Scout
    Agent -- not a parallel pipeline.
    """

    WEBSITE = "website"
    SOCIAL_MEDIA = "social_media"
    ECOMMERCE_PRODUCT = "ecommerce_product"


class SocialPlatform(str, Enum):
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    X = "x"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"


class SocialComparisonPlatform(str, Enum):
    """The social platforms a social-media comparison can run against.

    Deliberately narrower than :class:`SocialPlatform`, which describes handles
    a competitor *has*; this is the one platform a comparison is *about*.
    """

    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"


#: Hosts a link must belong to for each social comparison platform. Matched as
#: the host itself or a subdomain of it, so m.facebook.com passes and
#: facebook.com.example.net does not.
SOCIAL_PLATFORM_HOSTS: dict[SocialComparisonPlatform, tuple[str, ...]] = {
    SocialComparisonPlatform.FACEBOOK: ("facebook.com", "fb.com"),
    SocialComparisonPlatform.INSTAGRAM: ("instagram.com",),
}

SOCIAL_PLATFORM_LABELS: dict[SocialComparisonPlatform, str] = {
    SocialComparisonPlatform.FACEBOOK: "Facebook",
    SocialComparisonPlatform.INSTAGRAM: "Instagram",
}

#: Upper bound on any stored link.
#:
#: Marketplace links copied out of search results carry kilobytes of tracking
#: parameters -- a real Daraz product link runs past 1,100 characters -- so the
#: old 500-character cap rejected ordinary input. 8,192 is the request-line
#: limit most web servers enforce, so no link a site can actually serve is
#: longer; the bound exists only to stop a pathological payload.
MAX_URL_LENGTH = 8192

#: Shared cap for the two short free-text intake fields.
MAX_SHORT_TEXT = 120
#: What the business does: room for products, ordering terms and address (migration 0014).
MAX_DESCRIPTION = 500


def _is_http_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def _host_matches(url: str, allowed_hosts: tuple[str, ...]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == allowed or host.endswith(f".{allowed}") for allowed in allowed_hosts)


class SocialHandle(CamelModel):
    platform: SocialPlatform
    handle: str = Field(max_length=60)


class CompetitorInput(CamelModel):
    name: str = Field(min_length=2, max_length=120)
    landing_page_url: str = Field(max_length=MAX_URL_LENGTH)
    #: No longer collected by the intake form. Kept so existing rows and older
    #: clients still validate.
    social_handles: list[SocialHandle] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("landing_page_url")
    @classmethod
    def must_be_http_url(cls, value: str) -> str:
        value = value.strip()
        if not _is_http_url(value):
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
    #: The user's own link: a website, a social page or a product listing,
    #: depending on comparison_type. Required for all three.
    brand_website: str | None = Field(default=None, max_length=MAX_URL_LENGTH)
    brand_description: str = Field(max_length=MAX_DESCRIPTION)
    industry: Industry
    target_audience: str | None = Field(default=None, max_length=MAX_SHORT_TEXT)
    objectives: list[str] = Field(min_length=1, max_length=6)
    competitors: list[CompetitorInput] = Field(min_length=1, max_length=5)
    comparison_type: ComparisonType = ComparisonType.WEBSITE
    #: Only meaningful when comparison_type is ECOMMERCE_PRODUCT. Validated
    #: against the scraper registry rather than a hardcoded list, so a newly
    #: registered platform is accepted with no change here.
    ecommerce_platform: str | None = Field(default=None, max_length=40)
    #: Only meaningful when comparison_type is SOCIAL_MEDIA.
    social_platform: SocialComparisonPlatform | None = None

    @field_validator("objectives")
    @classmethod
    def objectives_not_blank(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("Add at least one objective")
        return cleaned

    @field_validator("brand_description")
    @classmethod
    def description_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Describe what the business does")
        return value

    @field_validator("target_audience", "brand_website")
    @classmethod
    def blank_is_none(cls, value: str | None) -> str | None:
        """An empty optional field arrives as "" from a form; store it as null."""
        value = (value or "").strip()
        return value or None

    @model_validator(mode="after")
    def check_type_specific_inputs(self) -> "ProjectCreate":
        """Enforces the rules that depend on what is being compared.

        Every comparison needs the user's own link, and a platform choice only
        survives on the comparison type it belongs to -- a Daraz platform on a
        website project would be dead data.
        """
        if self.comparison_type is not ComparisonType.ECOMMERCE_PRODUCT:
            self.ecommerce_platform = None
        if self.comparison_type is not ComparisonType.SOCIAL_MEDIA:
            self.social_platform = None

        if self.comparison_type is ComparisonType.ECOMMERCE_PRODUCT:
            self._check_ecommerce()
        elif self.comparison_type is ComparisonType.SOCIAL_MEDIA:
            self._check_social()
        else:
            self._require_own_link("Add your website link")

        return self

    def _require_own_link(self, missing_message: str) -> str:
        own = self.brand_website or ""
        if not own:
            raise ValueError(missing_message)
        if not _is_http_url(own):
            raise ValueError("Your link: enter a full URL, including https://")
        return own

    def _check_social(self) -> None:
        """Both pages must be on the platform the user picked, and that platform
        must be one something can actually read."""
        if self.social_platform is None:
            raise ValueError("Choose a social media platform to compare on")

        if source_kind_for("social_media", self.social_platform.value) not in source_kinds():
            # Facebook today: the option is listed so the plan is visible, but
            # there is no scraper behind it, and a project nothing can read
            # would only fail later.
            raise ValueError(
                f"{SOCIAL_PLATFORM_LABELS[self.social_platform]} comparisons are not available "
                "yet. Choose Instagram."
            )

        label = SOCIAL_PLATFORM_LABELS[self.social_platform]
        hosts = SOCIAL_PLATFORM_HOSTS[self.social_platform]
        article = "an" if label[0] in "AEIOU" else "a"

        own = self._require_own_link(f"Add your {label} page link")
        if not _host_matches(own, hosts):
            raise ValueError(f"Your platform link must be {article} {label} link ({hosts[0]})")

        for index, competitor in enumerate(self.competitors, start=1):
            if not _host_matches(competitor.landing_page_url, hosts):
                raise ValueError(
                    f"Competitor {index} platform link must be {article} {label} link ({hosts[0]})"
                )

    def _check_ecommerce(self) -> None:
        """The scraper needs a product page on both sides, and every link has
        to be one the selected platform can actually scrape."""
        if not self.ecommerce_platform:
            raise ValueError("Choose an e-commerce platform to compare on")
        if not is_supported(self.ecommerce_platform):
            supported = ", ".join(platform_keys()) or "none"
            raise ValueError(
                f"'{self.ecommerce_platform}' is not a supported platform. Supported: {supported}"
            )

        scraper = get_scraper(self.ecommerce_platform)

        own = self._require_own_link(
            f"Add your own {scraper.label} product link -- there is nothing to compare against without it"
        )
        try:
            scraper.validate_url(own)
        except Exception as exc:  # ScraperError; message is already user-facing
            raise ValueError(f"Your product link: {exc}") from exc

        own_canonical = scraper.canonical_url(own)
        for index, competitor in enumerate(self.competitors, start=1):
            try:
                scraper.validate_url(competitor.landing_page_url)
            except Exception as exc:
                raise ValueError(f"Competitor {index} product link: {exc}") from exc
            if scraper.canonical_url(competitor.landing_page_url) == own_canonical:
                raise ValueError(
                    f"Competitor {index} points at the same listing as yours -- "
                    "use a different product"
                )


class Project(CamelModel):
    id: str
    owner_id: str
    brand_name: str
    brand_website: str | None = None
    brand_description: str
    industry: Industry
    target_audience: str | None = None
    objectives: list[str] = Field(default_factory=list)
    comparison_type: ComparisonType = ComparisonType.WEBSITE
    ecommerce_platform: str | None = None
    social_platform: SocialComparisonPlatform | None = None
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
    #: One scraped marketplace listing. The structured fields behind it live in
    #: ``ecommerce_products``; this row is its entry in the sources list.
    ECOMMERCE_PRODUCT = "ecommerce_product"


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
