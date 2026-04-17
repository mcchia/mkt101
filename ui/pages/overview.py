"""Overview page: workflow + current operator state at a glance."""
from __future__ import annotations

from datetime import date

import streamlit as st

from models import IdeaStatus, SyncStatus
from storage import get_repository
from ui.components import freshness_label


def render() -> None:
    st.header("Overview")
    st.caption(
        "Data → Analysis → Ideas → Critique → Top 3 → Approval → Calendar. "
        "This page reflects your current state across that flow."
    )

    repo = get_repository()
    brand = repo.get_brand()
    posts = repo.list_posts()
    ideas = repo.list_ideas()
    calendar = repo.list_calendar()
    syncs = repo.list_syncs()

    # Top state row
    cols = st.columns(5)
    cols[0].metric("Posts stored", len(posts))
    cols[1].metric("Ideas", len(ideas))
    top3 = [i for i in ideas if i.selected_top3]
    cols[2].metric("Top 3 selected", len(top3))
    approved = [i for i in ideas if i.status == IdeaStatus.APPROVED]
    cols[3].metric("Approved", len(approved))
    cols[4].metric("Scheduled", len([c for c in calendar if c.scheduled_for >= date.today()]))

    st.divider()

    st.markdown("#### Workflow")
    workflow = [
        ("1 · Brand profile", bool(brand and brand.brand_name), "Brand Profile"),
        ("2 · Data ingested", bool(posts), "Data Sources"),
        ("3 · Performance analyzed", bool(st.session_state.get("analysis")), "Performance Analysis"),
        ("4 · Ideas generated", bool(ideas), "Idea Generation"),
        ("5 · Ideas scored", any(i.score.total() > 0 for i in ideas), "Idea Critique & Scoring"),
        ("6 · Top 3 picked", bool(top3), "Top 3 Recommendations"),
        ("7 · Calendar populated", bool(calendar), "Content Calendar"),
    ]
    for label, done, _next_page in workflow:
        mark = "✓" if done else "○"
        st.markdown(f"- **{mark}** {label}")

    st.divider()

    st.markdown("#### Data freshness")
    last_ok = next(
        (s for s in reversed(syncs) if s.status in (SyncStatus.OK, SyncStatus.PARTIAL)),
        None,
    )
    if last_ok:
        st.write(
            f"Last successful sync: **{last_ok.source.value}** — "
            f"{freshness_label(last_ok.finished_at or last_ok.started_at)}"
        )
        st.caption(f"Records ingested: {last_ok.records_ingested} · details: {last_ok.details or '—'}")
    else:
        st.info("No data ingested yet. Go to **Data Sources** to upload a CSV, crawl the brand site, or sync Meta.")

    if not brand or not brand.brand_name:
        st.warning(
            "Brand profile is empty. Fill in **Brand Profile** first — the assistant's output quality "
            "depends on knowing positioning, audience, tone, and pillars."
        )
