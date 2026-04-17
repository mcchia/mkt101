"""Brand profile and positioning memory."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class ContentPillar(BaseModel):
    name: str
    description: str = ""
    target_share_pct: Optional[int] = Field(default=None, ge=0, le=100)


class PostingConstraint(BaseModel):
    max_posts_per_week: int = 5
    preferred_platforms: list[str] = Field(default_factory=lambda: ["instagram", "facebook"])
    avoid_topics: list[str] = Field(default_factory=list)
    required_disclaimers: list[str] = Field(default_factory=list)
    blackout_days: list[str] = Field(default_factory=list)


class BrandProfile(BaseModel):
    """Persistent brand memory. A single-record document."""

    brand_name: str = ""
    website: str = ""
    one_liner: str = ""
    positioning: str = ""
    price_tier: str = "middle-to-high-end"
    target_audience: str = ""
    tone_of_voice: str = ""
    brand_values: list[str] = Field(default_factory=list)
    signature_products: list[str] = Field(default_factory=list)
    content_pillars: list[ContentPillar] = Field(default_factory=list)
    posting_constraints: PostingConstraint = Field(default_factory=PostingConstraint)
    premium_guardrails: list[str] = Field(
        default_factory=lambda: [
            "No aggressive discount-led messaging.",
            "No cheap, noisy, or childish visual language.",
            "No unverified health claims.",
            "No trend-chasing that conflicts with brand tone.",
        ]
    )
    forbidden_hooks: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)
