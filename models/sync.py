"""Sync run records for ingestion runs (CSV, crawler, Meta)."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class SyncStatus(str, Enum):
    RUNNING = "running"
    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"


class SyncSource(str, Enum):
    CSV = "csv"
    MANUAL = "manual"
    META_FACEBOOK = "meta_facebook"
    META_INSTAGRAM = "meta_instagram"
    WEBSITE_CRAWL = "website_crawl"
    PASTED_TEXT = "pasted_text"


class SyncRun(BaseModel):
    id: str = Field(default_factory=lambda: f"sync_{uuid4().hex[:10]}")
    source: SyncSource
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    status: SyncStatus = SyncStatus.RUNNING
    records_ingested: int = 0
    records_skipped: int = 0
    details: str = ""
    errors: list[str] = Field(default_factory=list)
    params: dict = Field(default_factory=dict)

    def finish(self, status: SyncStatus, details: str = "") -> None:
        self.status = status
        self.details = details
        self.finished_at = datetime.now(timezone.utc)
