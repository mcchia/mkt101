"""CSV + manual-table ingestion.

Accepts any CSV with columns the user can map via UI. Produces normalized
Post objects. Missing metric columns stay None — never fabricated.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from uuid import uuid4

from connectors.base import IngestionResult
from models import MediaType, Platform, Post, PostMetrics


@dataclass
class ColumnMapping:
    """Map CSV column names to internal field names. Unset = not provided."""

    id: str | None = None
    platform: str | None = None
    created_at: str | None = None
    caption: str | None = None
    media_type: str | None = None
    permalink: str | None = None
    pillar: str | None = None
    format_label: str | None = None
    # metrics
    impressions: str | None = None
    reach: str | None = None
    likes: str | None = None
    reactions: str | None = None
    comments: str | None = None
    shares: str | None = None
    saves: str | None = None
    clicks: str | None = None
    video_views: str | None = None
    conversions: str | None = None
    revenue: str | None = None

    @classmethod
    def default_guess(cls, headers: list[str]) -> "ColumnMapping":
        """Best-effort auto-map using common header synonyms."""
        lower = {h.lower().strip(): h for h in headers}

        def pick(*names: str) -> str | None:
            for n in names:
                if n in lower:
                    return lower[n]
            return None

        return cls(
            id=pick("id", "post_id", "post id"),
            platform=pick("platform", "channel", "network"),
            created_at=pick("created_at", "created", "date", "posted", "publish_date", "published"),
            caption=pick("caption", "text", "post_text", "copy", "description"),
            media_type=pick("media_type", "format", "media", "type"),
            permalink=pick("permalink", "url", "link"),
            pillar=pick("pillar", "theme", "category", "content_pillar"),
            format_label=pick("format_label", "format_tag", "format"),
            impressions=pick("impressions", "impr"),
            reach=pick("reach"),
            likes=pick("likes", "like"),
            reactions=pick("reactions"),
            comments=pick("comments", "comment_count"),
            shares=pick("shares", "share"),
            saves=pick("saves", "saved", "save"),
            clicks=pick("clicks", "link_clicks", "click"),
            video_views=pick("video_views", "views", "plays"),
            conversions=pick("conversions", "orders"),
            revenue=pick("revenue", "sales"),
        )


def _parse_int(raw: str | None) -> int | None:
    if raw is None:
        return None
    raw = str(raw).strip().replace(",", "")
    if not raw or raw.lower() in {"-", "n/a", "na", "none", "null"}:
        return None
    # handle values like "18.2k"
    if raw[-1:].lower() == "k":
        try:
            return int(float(raw[:-1]) * 1000)
        except ValueError:
            return None
    if raw[-1:].lower() == "m":
        try:
            return int(float(raw[:-1]) * 1_000_000)
        except ValueError:
            return None
    try:
        return int(float(raw))
    except ValueError:
        return None


def _parse_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    raw = str(raw).strip().replace(",", "").replace("$", "")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


_DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
]


def _parse_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    raw = str(raw).strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        pass
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        except ValueError:
            continue
    return None


def _parse_platform(raw: str | None) -> Platform:
    if not raw:
        return Platform.OTHER
    low = raw.strip().lower()
    if "insta" in low or low == "ig":
        return Platform.INSTAGRAM
    if "facebook" in low or low == "fb":
        return Platform.FACEBOOK
    return Platform.OTHER


def _parse_media(raw: str | None) -> MediaType:
    if not raw:
        return MediaType.UNKNOWN
    low = raw.strip().lower()
    mapping = {
        "image": MediaType.IMAGE,
        "photo": MediaType.IMAGE,
        "carousel": MediaType.CAROUSEL,
        "album": MediaType.CAROUSEL,
        "video": MediaType.VIDEO,
        "reel": MediaType.REEL,
        "story": MediaType.STORY,
        "text": MediaType.TEXT,
    }
    return mapping.get(low, MediaType.UNKNOWN)


class CsvIngestor:
    def ingest_text(
        self,
        csv_text: str,
        mapping: ColumnMapping | None = None,
    ) -> IngestionResult:
        result = IngestionResult()
        if not csv_text.strip():
            result.errors.append("Empty CSV content.")
            return result

        reader = csv.DictReader(io.StringIO(csv_text))
        headers = reader.fieldnames or []
        if not headers:
            result.errors.append("No header row found.")
            return result

        mapping = mapping or ColumnMapping.default_guess(headers)
        rows = list(reader)
        return self._ingest_rows(rows, mapping)

    def ingest_rows(
        self,
        rows: Iterable[dict],
        mapping: ColumnMapping,
    ) -> IngestionResult:
        return self._ingest_rows(list(rows), mapping)

    def _ingest_rows(
        self,
        rows: list[dict],
        mapping: ColumnMapping,
    ) -> IngestionResult:
        result = IngestionResult()
        for idx, row in enumerate(rows, start=1):
            try:
                post = self._row_to_post(row, mapping)
                if post is None:
                    result.skipped += 1
                    continue
                result.posts.append(post)
            except Exception as e:
                result.errors.append(f"Row {idx}: {e}")
                result.skipped += 1
        if not result.posts and not result.errors:
            result.warnings.append("No rows produced posts.")
        return result

    def _row_to_post(self, row: dict, mapping: ColumnMapping) -> Post | None:
        def g(col: str | None) -> str | None:
            if not col:
                return None
            val = row.get(col)
            if val is None:
                return None
            val = str(val).strip()
            return val or None

        caption = g(mapping.caption)
        metrics = PostMetrics(
            impressions=_parse_int(g(mapping.impressions)),
            reach=_parse_int(g(mapping.reach)),
            likes=_parse_int(g(mapping.likes)),
            reactions=_parse_int(g(mapping.reactions)),
            comments=_parse_int(g(mapping.comments)),
            shares=_parse_int(g(mapping.shares)),
            saves=_parse_int(g(mapping.saves)),
            clicks=_parse_int(g(mapping.clicks)),
            video_views=_parse_int(g(mapping.video_views)),
            conversions=_parse_int(g(mapping.conversions)),
            revenue=_parse_float(g(mapping.revenue)),
        )

        # If nothing useful parsed at all, skip the row.
        if not caption and not metrics.has_data() and not g(mapping.id):
            return None

        raw_id = g(mapping.id) or f"csv_{uuid4().hex[:10]}"
        return Post(
            id=raw_id,
            platform=_parse_platform(g(mapping.platform)),
            created_at=_parse_datetime(g(mapping.created_at)),
            caption=caption,
            media_type=_parse_media(g(mapping.media_type)),
            permalink=g(mapping.permalink),
            pillar=g(mapping.pillar),
            format_label=g(mapping.format_label),
            metrics=metrics,
            source="csv",
            raw=row,
        )
