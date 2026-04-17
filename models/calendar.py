"""Content calendar entries."""
from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class CalendarStatus(str, Enum):
    PLANNED = "planned"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    CANCELLED = "cancelled"


class CalendarEntry(BaseModel):
    id: str = Field(default_factory=lambda: f"cal_{uuid4().hex[:10]}")
    idea_id: Optional[str] = None
    scheduled_for: date
    platform: str = "instagram"
    title: str
    pillar: Optional[str] = None
    status: CalendarStatus = CalendarStatus.PLANNED
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
