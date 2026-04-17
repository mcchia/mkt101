"""Performance Analysis page: charts + LLM-driven fact/interpretation split."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st

from services.analysis import run_performance_analysis
from services.llm import LLMError
from storage import get_repository
from ui.components import posts_to_dataframe


def render() -> None:
    st.header("Performance Analysis")
    st.caption(
        "The assistant analyzes stored post data and returns facts, interpretations, "
        "assumptions, and data-quality caveats — separated."
    )

    repo = get_repository()
    posts = repo.list_posts()
    brand = repo.get_brand()
    ideas = repo.list_ideas()

    if not posts:
        st.info("No post data ingested yet. Upload a CSV, crawl, or sync Meta first.")
        return

    df = posts_to_dataframe(posts)

    # Top summary charts
    st.markdown("#### Descriptive view")
    chart_cols = st.columns(3)

    with chart_cols[0]:
        st.markdown("**By format**")
        by_format = df.groupby("media", dropna=False)[["reach", "saves", "clicks", "conversions"]].sum()
        st.bar_chart(by_format)

    with chart_cols[1]:
        st.markdown("**By pillar**")
        if df["pillar"].notna().any() and df["pillar"].str.len().gt(0).any():
            by_pillar = df.groupby("pillar", dropna=False)[["reach", "saves", "clicks"]].sum()
            st.bar_chart(by_pillar)
        else:
            st.caption("No pillar labels on data.")

    with chart_cols[2]:
        st.markdown("**Saves vs clicks vs conversions**")
        totals = df[["saves", "clicks", "conversions"]].sum(min_count=1)
        st.bar_chart(totals)

    st.markdown("#### Top / bottom posts")
    sort_key = st.selectbox(
        "Rank by",
        ["reach", "saves", "clicks", "conversions", "comments", "shares"],
        index=1,
    )
    ranked = df.sort_values(sort_key, ascending=False, na_position="last")
    cols = st.columns(2)
    with cols[0]:
        st.caption("Top 5")
        st.dataframe(ranked.head(5), use_container_width=True, hide_index=True)
    with cols[1]:
        st.caption("Bottom 5")
        st.dataframe(ranked.tail(5), use_container_width=True, hide_index=True)

    st.divider()

    # Analysis trigger
    st.markdown("#### LLM analysis")
    goal = st.text_area(
        "Goal / question (optional)",
        value=st.session_state.get("analysis_goal", ""),
        height=80,
        placeholder="e.g. drive saves and product-page clicks from existing buyers",
    )
    st.session_state["analysis_goal"] = goal

    if st.button("Run performance analysis", type="primary", use_container_width=True):
        with st.spinner("Analyzing…"):
            try:
                data, usage = run_performance_analysis(posts, brand, ideas, goal)
            except LLMError as e:
                st.error(str(e))
                return
        st.session_state["analysis"] = data
        st.session_state["analysis_usage"] = {
            "in": usage.input_tokens,
            "out": usage.output_tokens,
            "cache_read": usage.cache_read,
            "cache_write": usage.cache_write,
        }
        st.session_state["analysis_at"] = datetime.now(timezone.utc).isoformat()
        st.rerun()

    analysis: dict[str, Any] | None = st.session_state.get("analysis")
    if not analysis:
        return

    st.success(
        f"Analysis generated at {st.session_state.get('analysis_at', '')}. "
        f"Tokens: {st.session_state.get('analysis_usage', {})}"
    )

    st.markdown("##### Facts")
    for f in analysis.get("facts", []):
        st.markdown(f"- {f}")

    st.markdown("##### Interpretations")
    for f in analysis.get("interpretations", []):
        st.markdown(f"- {f}")

    st.markdown("##### Assumptions")
    for f in analysis.get("assumptions", []) or ["(none)"]:
        st.markdown(f"- {f}")

    cq = analysis.get("clarifying_questions", [])
    if cq:
        st.markdown("##### Clarifying questions")
        for q in cq:
            st.markdown(f"- {q}")

    cols = st.columns(2)
    with cols[0]:
        st.markdown("##### Working signals")
        for s in analysis.get("working_signals", []):
            st.markdown(
                f"- **{s.get('signal','')}** — {s.get('evidence','')} "
                f"_(confidence: {s.get('confidence','?')})_"
            )
    with cols[1]:
        st.markdown("##### Failing signals")
        for s in analysis.get("failing_signals", []):
            st.markdown(
                f"- **{s.get('signal','')}** — {s.get('evidence','')} "
                f"_(confidence: {s.get('confidence','?')})_"
            )

    pn = analysis.get("platform_notes") or {}
    if pn.get("instagram") or pn.get("facebook"):
        st.markdown("##### Platform notes")
        if pn.get("instagram"):
            st.markdown(f"- **Instagram** — {pn['instagram']}")
        if pn.get("facebook"):
            st.markdown(f"- **Facebook** — {pn['facebook']}")

    caveats = analysis.get("data_quality_caveats", [])
    if caveats:
        st.markdown("##### Data quality caveats")
        for c in caveats:
            st.markdown(f"- {c}")
