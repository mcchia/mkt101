"""Shared Streamlit UI components."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

import pandas as pd
import streamlit as st

from models import ContentIdea, IdeaStatus, Post
from services.scoring import brief_score_summary


STATUS_COLORS = {
    IdeaStatus.DRAFT: "#94a3b8",
    IdeaStatus.NEEDS_REVIEW: "#d97706",
    IdeaStatus.APPROVED: "#059669",
    IdeaStatus.SCHEDULED: "#2563eb",
    IdeaStatus.POSTED: "#0f766e",
    IdeaStatus.REJECTED: "#b91c1c",
}


def status_badge(status: IdeaStatus) -> str:
    color = STATUS_COLORS.get(status, "#475569")
    return (
        f"<span style='display:inline-block;padding:2px 8px;border-radius:8px;"
        f"background:{color};color:white;font-size:11px;"
        f"letter-spacing:0.02em;text-transform:uppercase;'>{status.value.replace('_',' ')}</span>"
    )


def freshness_label(last_dt: datetime | None) -> str:
    if not last_dt:
        return "no data"
    now = datetime.now(timezone.utc)
    delta = now - last_dt.replace(tzinfo=timezone.utc) if last_dt.tzinfo is None else now - last_dt
    hours = int(delta.total_seconds() // 3600)
    if hours < 1:
        return "fresh (< 1 hour)"
    if hours < 24:
        return f"{hours}h old"
    days = hours // 24
    if days < 14:
        return f"{days}d old"
    return f"{days // 7}w old"


def posts_to_dataframe(posts: Iterable[Post]) -> pd.DataFrame:
    rows = []
    for p in posts:
        m = p.metrics
        rows.append(
            {
                "id": p.id,
                "platform": p.platform.value,
                "created_at": p.created_at,
                "media": p.media_type.value,
                "pillar": p.pillar or "",
                "format": p.format_label or "",
                "reach": m.reach,
                "impressions": m.impressions,
                "likes": m.likes,
                "reactions": m.reactions,
                "comments": m.comments,
                "shares": m.shares,
                "saves": m.saves,
                "clicks": m.clicks,
                "conversions": m.conversions,
                "caption": (p.caption or "")[:120],
                "source": p.source,
            }
        )
    return pd.DataFrame(rows)


def render_idea_card(idea: ContentIdea) -> None:
    with st.container(border=True):
        top_cols = st.columns([3, 1])
        with top_cols[0]:
            st.markdown(f"**{idea.title}**")
            st.caption(
                f"{idea.platform} · {idea.format or 'format n/a'} · pillar: {idea.pillar or 'n/a'}"
            )
        with top_cols[1]:
            st.markdown(status_badge(idea.status), unsafe_allow_html=True)
        if idea.concept:
            st.write(idea.concept)
        if idea.why_now:
            st.caption(f"Why now: {idea.why_now}")
        if idea.score.total() > 0:
            st.caption(brief_score_summary(idea.score))


def usage_badge(usage: dict | None) -> None:
    if not usage:
        return
    st.caption(
        f"last call: in {usage.get('in', 0)} · out {usage.get('out', 0)} · "
        f"cache_read {usage.get('cache_read', 0)} · cache_write {usage.get('cache_write', 0)}"
    )


def info_split(label: str, value: str) -> None:
    cols = st.columns([1, 3])
    cols[0].markdown(f"**{label}**")
    cols[1].write(value)
