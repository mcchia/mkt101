"""Raw source records from external ingestion."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    WEBSITE_PAGE = "website_page"
    PRODUCT = "product"
    POST_RAW = "post_raw"
    NOTE = "note"


class SourceRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"src_{uuid4().hex[:10]}")
    source_type: SourceType
    source_run_id: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    content: str = ""
    structured: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
