"""Gaps, evidence and the HITL review record (stages 4-5)."""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from app.models.common import CamelModel


class GapCategory(str, Enum):
    CONTENT = "content"
    SEO = "seo"
    SOCIAL_ENGAGEMENT = "social_engagement"
    POSITIONING = "positioning"
    AUDIENCE = "audience"
    CONVERSION = "conversion"
    PRICING = "pricing"


class GapPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GapDecision(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Evidence(CamelModel):
    """A citation back to a scraped source. No agent claim ships without one."""

    source_id: str
    source_url: str
    source_title: str
    quote: str
    relevance: float = Field(ge=0.0, le=1.0)


class Gap(CamelModel):
    id: str
    project_id: str
    title: str
    description: str
    category: GapCategory
    priority: GapPriority
    #: Set by the reviewer at HITL #1; overrides the agent's own call.
    user_priority: GapPriority | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)
    opportunity: str
    decision: GapDecision = GapDecision.PENDING
    reviewer_note: str | None = None
    created_at: str


class GapPatch(CamelModel):
    """Partial update from the HITL #1 triage screen."""

    decision: GapDecision | None = None
    user_priority: GapPriority | None = None
    reviewer_note: str | None = Field(default=None, max_length=1000)


class ReviewDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class GapReviewSubmit(CamelModel):
    notes: str | None = Field(default=None, max_length=2000)
    accepted_gap_ids: list[str] = Field(min_length=1)


class HitlReview(CamelModel):
    """One human decision at either checkpoint. The audit trail."""

    id: str
    project_id: str
    #: 5 for gap refinement, 7 for final strategy approval.
    stage: int
    reviewer_id: str
    reviewer_name: str
    decision: ReviewDecision
    notes: str | None = None
    affected_ids: list[str] = Field(default_factory=list)
    created_at: str
