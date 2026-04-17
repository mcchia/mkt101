"""Shared shapes for all ingestion connectors."""
from __future__ import annotations

from dataclasses import dataclass, field

from models import Post


@dataclass
class IngestionResult:
    posts: list[Post] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped: int = 0


@dataclass
class MetricAvailability:
    """Which metrics a given source can or cannot provide."""

    available: list[str] = field(default_factory=list)
    unavailable: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
