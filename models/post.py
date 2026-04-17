"""Normalized post + metrics schema shared across platforms."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Platform(str, Enum):
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    OTHER = "other"


class MediaType(str, Enum):
    IMAGE = "image"
    CAROUSEL = "carousel"
    VIDEO = "video"
    REEL = "reel"
    STORY = "story"
    TEXT = "text"
    UNKNOWN = "unknown"


class PostMetrics(BaseModel):
    """Per-post metrics. Missing values stay None so we never fabricate."""

    impressions: Optional[int] = None
    reach: Optional[int] = None
    likes: Optional[int] = None
    reactions: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    saves: Optional[int] = None
    clicks: Optional[int] = None
    video_views: Optional[int] = None
    conversions: Optional[int] = None
    revenue: Optional[float] = None

    def has_data(self) -> bool:
        return any(v is not None for v in self.model_dump().values())


class Post(BaseModel):
    id: str
    platform: Platform
    created_at: Optional[datetime] = None
    caption: Optional[str] = None
    media_type: MediaType = MediaType.UNKNOWN
    permalink: Optional[str] = None
    hashtags: list[str] = Field(default_factory=list)
    pillar: Optional[str] = None
    format_label: Optional[str] = None
    metrics: PostMetrics = Field(default_factory=PostMetrics)
    source: str = "manual"
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw: dict = Field(default_factory=dict)

    def engagement_rate(self) -> Optional[float]:
        base = self.metrics.reach or self.metrics.impressions
        if not base:
            return None
        eng = sum(
            v or 0
            for v in [
                self.metrics.likes,
                self.metrics.reactions,
                self.metrics.comments,
                self.metrics.shares,
                self.metrics.saves,
            ]
        )
        return round(eng / base, 4) if base else None
