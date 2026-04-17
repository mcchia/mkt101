"""Top-posts pattern extractor.

Ranks content history records by a user-chosen metric (or a weighted score) and
extracts categorical patterns: hook type, caption length, CTA style, format,
pillar, and a rough visual hint if present. The output separates strong
(high-support) patterns from thin-data guesses.
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass
from typing import Any

from . import content_history, storage

_STORE = "top_patterns"

_HOOK_TYPE_RULES: list[tuple[str, str]] = [
    ("question", r"^\s*(?:how|why|what|which|when|where|can|does|is|are|do|did)\b.*\?"),
    ("number_list", r"^\s*\d{1,2}\s*(?:ways|tips|reasons|signs|things)\b"),
    ("contrarian", r"\b(?:stop|don'?t|never|unpopular opinion|contrary)\b"),
    ("story", r"\b(?:i used to|when i|my first|story time)\b"),
    ("curiosity", r"\b(?:you won'?t|the secret|nobody tells|most people)\b"),
    ("imperative", r"^\s*(?:try|meet|discover|taste|learn|brew)\b"),
]


def _classify_hook(hook: str) -> str:
    import re

    t = hook.lower().strip()
    if not t:
        return "unknown"
    for label, pattern in _HOOK_TYPE_RULES:
        if re.search(pattern, t):
            return label
    return "statement"


def _caption_length_bucket(text: str) -> str:
    n = len(text or "")
    if n <= 120:
        return "short (<=120)"
    if n <= 350:
        return "medium (120-350)"
    return "long (>350)"


def _cta_style(cta: str) -> str:
    import re

    t = (cta or "").lower().strip()
    if not t:
        return "none"
    if re.search(r"\b(shop|buy|order|purchase|add to cart)\b", t):
        return "direct_purchase"
    if re.search(r"\b(save|bookmark|keep this)\b", t):
        return "save"
    if re.search(r"\b(comment|reply|tell us|share)\b", t):
        return "engage"
    if re.search(r"\b(sign up|subscribe|join)\b", t):
        return "signup"
    if re.search(r"\b(learn|read|see|explore|discover)\b", t):
        return "learn_more"
    return "other"


AVAILABLE_METRICS = ["reach", "likes", "saves", "comments", "clicks", "orders", "weighted"]


def _weighted_score(metrics: dict[str, float]) -> float:
    weights = {
        "orders": 5.0,
        "clicks": 2.0,
        "saves": 1.5,
        "comments": 1.2,
        "likes": 0.5,
        "reach": 0.05,
    }
    total = 0.0
    for k, w in weights.items():
        v = float(metrics.get(k, 0) or 0)
        total += w * v
    return total


def _score(record: content_history.PostRecord, metric: str) -> float:
    if metric == "weighted":
        return _weighted_score(record.metrics)
    return float(record.metrics.get(metric, 0) or 0)


@dataclass
class PatternRow:
    dimension: str
    value: str
    support: int  # how many records in the top set
    share: float  # top_support / sample_size
    avg_score: float


@dataclass
class PatternReport:
    metric: str
    top_n: int
    sample_size: int
    patterns: list[PatternRow]
    strong: list[PatternRow]
    thin: list[PatternRow]
    summary: str


def extract(metric: str = "weighted", top_n: int = 5) -> PatternReport:
    if metric not in AVAILABLE_METRICS:
        raise ValueError(f"metric must be one of {AVAILABLE_METRICS}")
    recs = content_history.list_records()
    sample_size = len(recs)
    if sample_size == 0:
        return PatternReport(
            metric=metric,
            top_n=0,
            sample_size=0,
            patterns=[],
            strong=[],
            thin=[],
            summary="No content history yet. Add posts to extract patterns.",
        )
    ranked = sorted(recs, key=lambda r: _score(r, metric), reverse=True)
    top = ranked[: max(1, min(top_n, sample_size))]
    top_len = len(top)

    def _rows(dimension: str, values: list[tuple[str, float]]) -> list[PatternRow]:
        bucket_scores: dict[str, list[float]] = {}
        for value, score in values:
            bucket_scores.setdefault(value, []).append(score)
        rows: list[PatternRow] = []
        for value, scores in bucket_scores.items():
            rows.append(
                PatternRow(
                    dimension=dimension,
                    value=value,
                    support=len(scores),
                    share=len(scores) / top_len,
                    avg_score=sum(scores) / len(scores),
                )
            )
        rows.sort(key=lambda r: (-r.support, -r.avg_score))
        return rows

    scored_top = [(r, _score(r, metric)) for r in top]
    hook_rows = _rows("hook_type", [(_classify_hook(r.hook), s) for r, s in scored_top])
    caption_rows = _rows(
        "caption_length",
        [(_caption_length_bucket(r.notes or r.hook), s) for r, s in scored_top],
    )
    cta_rows = _rows("cta_style", [(_cta_style(r.cta), s) for r, s in scored_top])
    format_rows = _rows("format", [((r.format or "unknown").lower(), s) for r, s in scored_top])
    pillar_rows = _rows("pillar", [((r.pillar or "unknown").lower(), s) for r, s in scored_top])
    platform_rows = _rows("platform", [((r.platform or "unknown").lower(), s) for r, s in scored_top])

    all_rows = hook_rows + caption_rows + cta_rows + format_rows + pillar_rows + platform_rows

    strong: list[PatternRow] = []
    thin: list[PatternRow] = []
    threshold_strong = 3 if top_len >= 5 else 2
    for row in all_rows:
        if row.support >= threshold_strong:
            strong.append(row)
        else:
            thin.append(row)

    summary_bits: list[str] = []
    for row in strong[:5]:
        summary_bits.append(
            f"{row.dimension}={row.value} ({row.support}/{top_len}, share {row.share:.0%})"
        )
    if sample_size < 5:
        summary = f"Thin data (n={sample_size}). Patterns below are directional only."
        if summary_bits:
            summary += " " + "; ".join(summary_bits)
    else:
        summary = (
            f"Top {top_len} of {sample_size} by {metric}. "
            + ("; ".join(summary_bits) if summary_bits else "No recurring pattern reached strong support.")
        )

    rep = PatternReport(
        metric=metric,
        top_n=top_len,
        sample_size=sample_size,
        patterns=all_rows,
        strong=strong,
        thin=thin,
        summary=summary,
    )
    _save_summary(rep)
    return rep


def _save_summary(rep: PatternReport) -> None:
    storage.save(
        _STORE,
        {
            "generated_at": int(time.time()),
            "metric": rep.metric,
            "sample_size": rep.sample_size,
            "top_n": rep.top_n,
            "summary": rep.summary,
            "strong": [row.__dict__ for row in rep.strong],
            "thin": [row.__dict__ for row in rep.thin],
        },
    )


def last_saved_summary() -> dict[str, Any] | None:
    doc = storage.load(_STORE, None)
    return doc if isinstance(doc, dict) else None


def system_block() -> str:
    doc = last_saved_summary()
    if not doc:
        return ""
    lines = [f"## Winning-post patterns (metric: {doc.get('metric')})", doc.get("summary", "")]
    strong = doc.get("strong", [])
    if strong:
        lines.append("Strong patterns (use sparingly, avoid clone-ish output):")
        for r in strong[:8]:
            lines.append(
                f"- {r.get('dimension')}={r.get('value')} "
                f"support={r.get('support')} share={float(r.get('share', 0)):.0%}"
            )
    return "\n".join(lines)
