"""Portable mirror of backend/app/models/gap.py for notebook-only execution."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    source_id: str
    source_url: str
    source_title: str
    quote: str
    relevance: float = Field(ge=0, le=1)


class Gap(BaseModel):
    id: str
    project_id: str
    title: str
    description: str
    category: str = Field(pattern="^(content|seo|social_engagement|positioning|audience|conversion|pricing)$")
    priority: str = Field(pattern="^(critical|high|medium|low)$")
    confidence: float = Field(ge=0, le=1)
    evidence: list[Evidence] = Field(min_length=1)
    opportunity: str
    created_at: datetime

