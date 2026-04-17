"""Content history tracker.

Stores normalized post records and detects repetition/fatigue signals on
hooks, angles, formats, CTAs, and content pillars.

Records are intentionally lightweight: a free-form "hook" string plus
categorical fields. Normalization is done with simple lowercasing, token
stripping, and synonym folding so small wording differences still collapse.
"""

from __future__ import annotations

import hashlib
import re
import time
import uuid
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

from . import storage

_STORE = "content_history"

_FORMAT_SYNONYMS = {
    "reel": "reel",
    "reels": "reel",
    "video": "reel",
    "short": "reel",
    "story": "story",
    "stories": "story",
    "carousel": "carousel",
    "slides": "carousel",
    "post": "static",
    "static": "static",
    "image": "static",
    "photo": "static",
    "live": "live",
    "ugc": "ugc",
}


@dataclass
class PostRecord:
    id: str
    posted_at: str  # ISO-like string or free-form; UI renders as text
    platform: str  # e.g., "instagram", "facebook"
    hook: str
    angle: str
    format: str
    cta: str
    pillar: str
    metrics: dict[str, float]  # reach, likes, saves, comments, clicks, orders...
    notes: str = ""


def _load() -> list[dict[str, Any]]:
    data = storage.load(_STORE, [])
    return data if isinstance(data, list) else []


def _save(records: list[dict[str, Any]]) -> None:
    storage.save(_STORE, records)


def _norm_text(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _norm_format(s: str) -> str:
    n = _norm_text(s)
    return _FORMAT_SYNONYMS.get(n, n)


def _hook_key(s: str) -> str:
    n = _norm_text(s)
    # collapse to a short signature so slightly reworded hooks still match
    tokens = [t for t in n.split() if len(t) > 2]
    key = " ".join(tokens[:8])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]


def list_records() -> list[PostRecord]:
    return [_to_record(r) for r in _load()]


def _to_record(raw: dict[str, Any]) -> PostRecord:
    return PostRecord(
        id=str(raw.get("id") or uuid.uuid4().hex),
        posted_at=str(raw.get("posted_at", "")),
        platform=str(raw.get("platform", "")),
        hook=str(raw.get("hook", "")),
        angle=str(raw.get("angle", "")),
        format=str(raw.get("format", "")),
        cta=str(raw.get("cta", "")),
        pillar=str(raw.get("pillar", "")),
        metrics={k: float(v) for k, v in (raw.get("metrics") or {}).items() if _is_num(v)},
        notes=str(raw.get("notes", "")),
    )


def _is_num(v: Any) -> bool:
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def add_record(
    *,
    posted_at: str,
    platform: str,
    hook: str,
    angle: str,
    format: str,
    cta: str,
    pillar: str,
    metrics: dict[str, float] | None = None,
    notes: str = "",
) -> PostRecord:
    rec = PostRecord(
        id=uuid.uuid4().hex[:12],
        posted_at=posted_at.strip(),
        platform=platform.strip().lower(),
        hook=hook.strip(),
        angle=angle.strip(),
        format=format.strip(),
        cta=cta.strip(),
        pillar=pillar.strip(),
        metrics=metrics or {},
        notes=notes.strip(),
    )
    records = _load()
    records.append(rec.__dict__)
    _save(records)
    return rec


def delete_record(record_id: str) -> bool:
    records = _load()
    new = [r for r in records if r.get("id") != record_id]
    if len(new) == len(records):
        return False
    _save(new)
    return True


def clear_all() -> None:
    _save([])


def import_records(records: Iterable[dict[str, Any]]) -> int:
    """Bulk import. Returns count added. Ignores rows without a hook."""
    existing = _load()
    added = 0
    for raw in records:
        hook = str(raw.get("hook", "")).strip()
        if not hook:
            continue
        rec = PostRecord(
            id=uuid.uuid4().hex[:12],
            posted_at=str(raw.get("posted_at", "")).strip(),
            platform=str(raw.get("platform", "")).strip().lower(),
            hook=hook,
            angle=str(raw.get("angle", "")).strip(),
            format=str(raw.get("format", "")).strip(),
            cta=str(raw.get("cta", "")).strip(),
            pillar=str(raw.get("pillar", "")).strip(),
            metrics={k: float(v) for k, v in (raw.get("metrics") or {}).items() if _is_num(v)},
            notes=str(raw.get("notes", "")).strip(),
        )
        existing.append(rec.__dict__)
        added += 1
    _save(existing)
    return added


# ------- Fatigue analysis -----------------------------------------------------


@dataclass
class FatigueReport:
    pillar_counts: Counter
    format_counts: Counter
    cta_counts: Counter
    hook_clusters: list[tuple[str, int]]
    angle_clusters: list[tuple[str, int]]
    warnings: list[str]


def analyze_fatigue(lookback: int = 20) -> FatigueReport:
    recs = list_records()[-max(1, lookback):]
    pillar_counts = Counter(_norm_text(r.pillar) for r in recs if r.pillar)
    format_counts = Counter(_norm_format(r.format) for r in recs if r.format)
    cta_counts = Counter(_norm_text(r.cta) for r in recs if r.cta)

    hook_by_key: dict[str, tuple[str, int]] = {}
    for r in recs:
        k = _hook_key(r.hook)
        if not k:
            continue
        existing = hook_by_key.get(k)
        hook_by_key[k] = (r.hook, (existing[1] if existing else 0) + 1)
    hook_clusters = sorted(hook_by_key.values(), key=lambda x: -x[1])

    angle_counts: Counter = Counter(_norm_text(r.angle) for r in recs if r.angle)
    angle_clusters = [(a, c) for a, c in angle_counts.most_common() if a]

    warnings: list[str] = []
    total = len(recs)
    if total:
        for pillar, c in pillar_counts.most_common(1):
            if c / total >= 0.5 and total >= 4:
                warnings.append(
                    f"Pillar concentration: '{pillar}' is {c}/{total} of recent posts."
                )
        for fmt, c in format_counts.most_common(1):
            if c / total >= 0.6 and total >= 4:
                warnings.append(
                    f"Format concentration: '{fmt}' is {c}/{total} of recent posts."
                )
        for cta, c in cta_counts.most_common(1):
            if c / total >= 0.5 and total >= 4:
                warnings.append(
                    f"CTA fatigue: '{cta}' is {c}/{total} of recent posts."
                )
        for hook, c in hook_clusters[:1]:
            if c >= 3:
                warnings.append(
                    f"Repeated hook ({c}x): {hook[:80]}"
                )
    return FatigueReport(
        pillar_counts=pillar_counts,
        format_counts=format_counts,
        cta_counts=cta_counts,
        hook_clusters=hook_clusters,
        angle_clusters=angle_clusters,
        warnings=warnings,
    )


def similarity_warnings(proposed_hook: str, proposed_angle: str, lookback: int = 20) -> list[str]:
    """Warn if a proposed idea looks too close to a recent record."""
    warnings: list[str] = []
    recs = list_records()[-max(1, lookback):]
    if not recs:
        return warnings
    pk = _hook_key(proposed_hook)
    pn_angle = _norm_text(proposed_angle)
    for r in recs:
        if pk and pk == _hook_key(r.hook):
            warnings.append(f"Hook is very close to a recent post on {r.posted_at or 'unknown date'}: {r.hook[:80]}")
            break
    if pn_angle:
        for r in recs:
            if pn_angle and pn_angle == _norm_text(r.angle):
                warnings.append(f"Angle matches a recent post on {r.posted_at or 'unknown date'}: {r.angle[:80]}")
                break
    return warnings


def system_block(lookback: int = 20) -> str:
    """Compact recent-history context for idea generation awareness."""
    recs = list_records()[-max(1, lookback):]
    if not recs:
        return ""
    rep = analyze_fatigue(lookback=lookback)
    lines = ["## Recent content history (most recent last; avoid repeating)"]
    for r in recs[-min(10, len(recs)):]:
        lines.append(
            f"- {r.posted_at or '?'} [{r.platform or '?'}] pillar={r.pillar or '?'} | "
            f"format={r.format or '?'} | hook={r.hook[:70]} | cta={r.cta or '?'}"
        )
    if rep.warnings:
        lines.append("\nFatigue signals:")
        for w in rep.warnings:
            lines.append(f"- {w}")
    lines.append(
        "\nWhen generating ideas, vary hook, angle, format, CTA, and pillar away from "
        "the above. Flag if a new idea is too close to a recent post."
    )
    return "\n".join(lines)
