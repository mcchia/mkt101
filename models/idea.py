"""Content ideas, scoring, critique, and execution briefs."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class IdeaStatus(str, Enum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    REJECTED = "rejected"


class IdeaScore(BaseModel):
    """Transparent scoring. 0-10 each. Weighted sum computed at runtime."""

    brand_fit: float = Field(ge=0, le=10, default=0)
    audience_relevance: float = Field(ge=0, le=10, default=0)
    engagement_potential: float = Field(ge=0, le=10, default=0)
    conversion_support: float = Field(ge=0, le=10, default=0)
    originality: float = Field(ge=0, le=10, default=0)
    production_ease: float = Field(ge=0, le=10, default=0)
    premium_safety: float = Field(ge=0, le=10, default=0)

    def total(self) -> float:
        weights = {
            "brand_fit": 0.18,
            "audience_relevance": 0.15,
            "engagement_potential": 0.13,
            "conversion_support": 0.17,
            "originality": 0.10,
            "production_ease": 0.07,
            "premium_safety": 0.20,
        }
        return round(
            sum(getattr(self, k) * w for k, w in weights.items()),
            2,
        )


class IdeaCritique(BaseModel):
    likely_upside: str = ""
    likely_weakness: str = ""
    risks: list[str] = Field(default_factory=list)
    why_not_top: Optional[str] = None


class ExecutionBrief(BaseModel):
    hook: str = ""
    angle: str = ""
    draft_caption: str = ""
    creative_direction: str = ""
    asset_requirements: list[str] = Field(default_factory=list)
    cta: str = ""
    platform_fit: list[str] = Field(default_factory=list)
    recommended_order: Optional[int] = None
    kpis_to_monitor: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)


class ContentIdea(BaseModel):
    id: str = Field(default_factory=lambda: f"idea_{uuid4().hex[:10]}")
    batch_id: str = ""
    title: str
    concept: str = ""
    objective: str = ""
    audience_angle: str = ""
    platform: str = "instagram"
    format: str = ""
    pillar: Optional[str] = None
    why_now: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    score: IdeaScore = Field(default_factory=IdeaScore)
    critique: IdeaCritique = Field(default_factory=IdeaCritique)
    brief: Optional[ExecutionBrief] = None
    status: IdeaStatus = IdeaStatus.DRAFT
    notes: str = ""
    selected_top3: bool = False
    top3_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)
