"""The 9-stage pipeline. Mirrors frontend/src/types/pipeline.ts."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import Field

from app.models.common import CamelModel

StageId = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]

#: The two mandatory human-in-the-loop checkpoints.
CHECKPOINT_STAGES: tuple[int, ...] = (5, 7)


class StageActor(str, Enum):
    HUMAN = "human"
    AGENT = "agent"
    SYSTEM = "system"


class StageStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    AWAITING_HUMAN = "awaiting_human"
    COMPLETE = "complete"
    ERROR = "error"
    SKIPPED = "skipped"


class StageKey(str, Enum):
    INPUT = "input"
    SCOUT = "scout"
    PREPROCESS = "preprocess"
    INSIGHT = "insight"
    REVIEW_GAPS = "review_gaps"
    STRATEGY = "strategy"
    REVIEW_STRATEGY = "review_strategy"
    DOCUMENT = "document"
    AUTOMATION = "automation"


class StageMetrics(CamelModel):
    items_processed: int = 0
    duration_ms: int = 0
    #: None for stages that make no LLM calls (1, 3, 5, 7).
    tokens_used: int | None = None
    cost_usd: float | None = None
    #: Why parts of the stage produced nothing (e.g. too few comments), shown
    #: to the reviewer so an empty result is never a mystery.
    notes: list[str] = []
    #: Stage 4 (Instagram): what each part of the analysis found.
    analysis: list[dict] | None = None


class StageState(CamelModel):
    id: int
    status: StageStatus = StageStatus.IDLE
    progress: int = Field(default=0, ge=0, le=100)
    started_at: str | None = None
    completed_at: str | None = None
    message: str | None = None
    error: str | None = None
    metrics: StageMetrics | None = None


class PipelineState(CamelModel):
    project_id: str
    current_stage: int = 1
    stages: dict[int, StageState]
    #: Set when parked at stage 5 or 7 waiting on a person.
    blocked_on: int | None = None
    updated_at: str


#: Stage metadata, kept in step with frontend/src/lib/pipeline-stages.ts.
STAGE_DEFINITIONS: dict[int, dict[str, object]] = {
    1: {"key": StageKey.INPUT, "title": "User Input", "actor": StageActor.HUMAN},
    2: {"key": StageKey.SCOUT, "title": "Scout Agent", "actor": StageActor.AGENT},
    3: {"key": StageKey.PREPROCESS, "title": "Preprocessing & Storage", "actor": StageActor.SYSTEM},
    4: {"key": StageKey.INSIGHT, "title": "Insight Agent", "actor": StageActor.AGENT},
    5: {
        "key": StageKey.REVIEW_GAPS,
        "title": "Human Review - Gap Refinement",
        "actor": StageActor.HUMAN,
    },
    6: {"key": StageKey.STRATEGY, "title": "Strategist + Critic", "actor": StageActor.AGENT},
    7: {
        "key": StageKey.REVIEW_STRATEGY,
        "title": "Human Review - Final Approval",
        "actor": StageActor.HUMAN,
    },
    8: {"key": StageKey.DOCUMENT, "title": "Strategy Document", "actor": StageActor.SYSTEM},
    9: {"key": StageKey.AUTOMATION, "title": "Scalability & Automation", "actor": StageActor.AGENT},
}