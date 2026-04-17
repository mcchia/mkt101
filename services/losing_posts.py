"""Losing-post detector.

Mirror of patterns.py but operating on the bottom of the ranking. Surfaces
content styles that consistently underperform and attaches a stop/reduce/retest
recommendation based on evidence strength.
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass
from typing import Any

from . import content_history, patterns, storage

_STORE = "losing_patterns"


@dataclass
class LosingRow:
    dimension: str
    value: str
    support: int
    share: float
    avg_score: float
    evidence: str  # "weak" | "strong"
    recommendation: str  # "stop" | "reduce" | "retest"
    reason: str


@dataclass
class LosingReport:
    metric: str
    bottom_n: int
    sample_size: int
    rows: list[LosingRow]
    summary: str


def _row(
    dimension: str,
    value: str,
    support: int,
    bottom_len: int,
    avg_score: float,
    overall_share: float,
) -> LosingRow:
    share = support / bottom_len if bottom_len else 0
    # Strong evidence: present in >= half of bottom AND under-represented in top share.
    if support >= max(3, bottom_len // 2):
        evidence = "strong"
        recommendation = "stop" if share >= 0.6 else "reduce"
    else:
        evidence = "weak"
        recommendation = "retest"

    reason_bits = [
        f"Appears in {support}/{bottom_len} of worst performers ({share:.0%})"
    ]
    if avg_score == 0:
        reason_bits.append("average score on this slice is zero")
    return LosingRow(
        dimension=dimension,
        value=value,
        support=support,
        share=share,
        avg_score=avg_score,
        evidence=evidence,
        recommendation=recommendation,
        reason=". ".join(reason_bits) + ".",
    )


def extract(metric: str = "weighted", bottom_n: int = 5) -> LosingReport:
    recs = content_history.list_records()
    sample = len(recs)
    if sample == 0:
        return LosingReport(metric=metric, bottom_n=0, sample_size=0, rows=[], summary="No content history.")

    ranked = sorted(recs, key=lambda r: patterns._score(r, metric))
    bottom = ranked[: max(1, min(bottom_n, sample))]
    blen = len(bottom)

    def bucket(values: list[tuple[str, float]]) -> dict[str, list[float]]:
        out: dict[str, list[float]] = {}
        for v, s in values:
            out.setdefault(v, []).append(s)
        return out

    scored = [(r, patterns._score(r, metric)) for r in bottom]

    hooks = bucket([(patterns._classify_hook(r.hook), s) for r, s in scored])
    ctas = bucket([(patterns._cta_style(r.cta), s) for r, s in scored])
    formats = bucket([((r.format or "unknown").lower(), s) for r, s in scored])
    pillars = bucket([((r.pillar or "unknown").lower(), s) for r, s in scored])

    rows: list[LosingRow] = []
    for dimension, buckets in [
        ("hook_type", hooks),
        ("cta_style", ctas),
        ("format", formats),
        ("pillar", pillars),
    ]:
        for value, scores in buckets.items():
            avg = sum(scores) / len(scores) if scores else 0
            rows.append(
                _row(
                    dimension=dimension,
                    value=value,
                    support=len(scores),
                    bottom_len=blen,
                    avg_score=avg,
                    overall_share=len(scores) / sample,
                )
            )

    rows.sort(key=lambda r: (0 if r.evidence == "strong" else 1, -r.support))

    summary_bits = [f"{r.dimension}={r.value} ({r.recommendation}, {r.evidence})" for r in rows[:5]]
    if sample < 5:
        summary = f"Thin data (n={sample}). Treat findings below as directional."
    else:
        summary = (
            f"Bottom {blen} of {sample} by {metric}. "
            + ("; ".join(summary_bits) if summary_bits else "No clear losing pattern.")
        )

    rep = LosingReport(metric=metric, bottom_n=blen, sample_size=sample, rows=rows, summary=summary)
    storage.save(
        _STORE,
        {
            "generated_at": int(time.time()),
            "metric": metric,
            "sample_size": sample,
            "bottom_n": blen,
            "summary": summary,
            "rows": [r.__dict__ for r in rows],
        },
    )
    return rep


def last_saved_summary() -> dict[str, Any] | None:
    doc = storage.load(_STORE, None)
    return doc if isinstance(doc, dict) else None


def system_block() -> str:
    doc = last_saved_summary()
    if not doc:
        return ""
    lines = [f"## Losing-post patterns (metric: {doc.get('metric')})", doc.get("summary", "")]
    for r in doc.get("rows", [])[:6]:
        lines.append(
            f"- {r.get('dimension')}={r.get('value')} -> {r.get('recommendation')} "
            f"({r.get('evidence')}; support={r.get('support')})"
        )
    lines.append("Avoid repeating the 'stop'-rated combinations in new ideas.")
    return "\n".join(lines)
