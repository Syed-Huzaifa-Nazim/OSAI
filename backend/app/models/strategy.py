"""Strategy, Critic feedback and the stage-7 decision (stages 6-7)."""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from app.models.common import CamelModel
from app.models.gap import ReviewDecision


class StrategyStatus(str, Enum):
    GENERATING = "generating"
    DRAFT = "draft"
    CRITIQUED = "critiqued"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REVISION_REQUESTED = "revision_requested"


class InitiativeEffort(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CriticVerdict(str, Enum):
    STRENGTHENED = "strengthened"
    CHALLENGED = "challenged"
    REJECTED = "rejected"
    APPROVED = "approved"


class CriticDimension(str, Enum):
    STRENGTH = "strength"
    CLARITY = "clarity"
    FEASIBILITY = "feasibility"
    EVIDENCE = "evidence"


class CriticSeverity(str, Enum):
    INFO = "info"
    MINOR = "minor"
    MAJOR = "major"


class Initiative(CamelModel):
    id: str
    title: str
    rationale: str
    actions: list[str] = Field(default_factory=list)
    channel: str
    effort: InitiativeEffort
    expected_impact: str
    timeline_weeks: int = Field(ge=1, le=52)
    linked_gap_ids: list[str] = Field(default_factory=list)
    revised_from_draft: bool = False


class CriticFeedback(CamelModel):
    """One Critic intervention.

    ``before`` and ``after`` are both kept so the transparency panel can show
    exactly what changed between the Strategist's draft and the final text.
    Dropping them would make the product's central claim unverifiable.
    """

    id: str
    target_initiative_id: str | None = None
    verdict: CriticVerdict
    dimension: CriticDimension
    comment: str
    before: str | None = None
    after: str | None = None
    severity: CriticSeverity = CriticSeverity.INFO


class Strategy(CamelModel):
    id: str
    project_id: str
    version: int = 1
    title: str
    executive_summary: str
    status: StrategyStatus = StrategyStatus.DRAFT
    initiatives: list[Initiative] = Field(default_factory=list)
    critic_feedback: list[CriticFeedback] = Field(default_factory=list)
    addressed_gap_ids: list[str] = Field(default_factory=list)
    generated_at: str
    approved_at: str | None = None


class StrategyReviewSubmit(CamelModel):
    decision: ReviewDecision
    notes: str | None = Field(default=None, max_length=2000)
    flagged_ids: list[str] = Field(default_factory=list)
