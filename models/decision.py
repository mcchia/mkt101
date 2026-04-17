"""Audit trail for approval decisions."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class DecisionLogEntry(BaseModel):
    id: str = Field(default_factory=lambda: f"dec_{uuid4().hex[:10]}")
    entity_type: str  # "idea" | "calendar" | "brand" | ...
    entity_id: str
    action: str  # "approve" | "reject" | "edit" | "schedule" | ...
    from_status: str | None = None
    to_status: str | None = None
    actor: str = "user"
    note: str = ""
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
