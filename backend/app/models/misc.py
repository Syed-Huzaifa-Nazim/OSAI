"""Cost tracking, integrations, contact and auth-adjacent models."""

from __future__ import annotations

from enum import Enum

from pydantic import EmailStr, Field

from app.models.common import CamelModel


class StageCost(CamelModel):
    stage: int
    tokens: int = 0
    cost_usd: float = 0.0


class RunCost(CamelModel):
    """Per-run LLM spend. Surfaced in the UI so cost is visible, not hidden."""

    project_id: str
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    by_stage: list[StageCost] = Field(default_factory=list)


class IntegrationStatus(str, Enum):
    AVAILABLE = "available"
    CONNECTED = "connected"
    COMING_SOON = "coming_soon"
    ERROR = "error"


class Integration(CamelModel):
    """Registry row for a teammate's separately-built feature module."""

    id: str
    feature_key: str
    name: str
    description: str
    status: IntegrationStatus = IntegrationStatus.AVAILABLE
    connected_at: str | None = None
    config: dict[str, str] | None = None


class ContactSubmission(CamelModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    organisation: str | None = Field(default=None, max_length=120)
    message: str = Field(min_length=20, max_length=2000)


class UserProfile(CamelModel):
    id: str
    email: str
    full_name: str | None = None
    avatar_url: str | None = None
    created_at: str


class HealthResponse(CamelModel):
    status: str
    version: str
    environment: str
    demo_mode: bool
    supabase_configured: bool
    openai_configured: bool
    vectorstore_available: bool
