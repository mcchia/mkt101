"""Patterns + losing posts page."""

from __future__ import annotations

import streamlit as st

from services import losing_posts, patterns
from ui import styling


def render() -> None:
    styling.page_header(
        "Patterns & Losing Posts",
        subtitle=(
            "Extract patterns from winners and losers in your content history. "
            "Strong-evidence patterns are separated from thin-data guesses."
        ),
        eyebrow="Knowledge",
    )

    with styling.card():
        col_m, col_t, col_b, col_r = st.columns([2, 1, 1, 1])
        with col_m:
            metric = st.selectbox(
                "Winning metric",
                patterns.AVAILABLE_METRICS,
                index=patterns.AVAILABLE_METRICS.index("weighted"),
            )
        with col_t:
            top_n = st.number_input("Top N", min_value=3, max_value=20, value=5, step=1)
        with col_b:
            bottom_n = st.number_input("Bottom N", min_value=3, max_value=20, value=5, step=1)
        with col_r:
            st.write("")
            st.write("")
            run = st.button("Run extraction", type="primary", use_container_width=True)

    tab_top, tab_lose = st.tabs(["Winners", "Losers"])

    with tab_top:
        if run:
            rep = patterns.extract(metric=metric, top_n=int(top_n))
            _render_top(rep)
        else:
            doc = patterns.last_saved_summary()
            if doc:
                _render_top_saved(doc)
            else:
                styling.empty_state(
                    "No extraction yet",
                    "Run extraction to see which hooks, formats, CTAs, and pillars correlate with winners.",
                )

    with tab_lose:
        if run:
            rep = losing_posts.extract(metric=metric, bottom_n=int(bottom_n))
            _render_losing(rep)
        else:
            doc = losing_posts.last_saved_summary()
            if doc:
                _render_losing_saved(doc)
            else:
                styling.empty_state(
                    "No extraction yet",
                    "Run extraction to surface stop / reduce / retest candidates.",
                )


def _render_top(rep: patterns.PatternReport) -> None:
    st.markdown(rep.summary)
    if rep.strong:
        styling.section("Strong patterns")
        st.dataframe(
            [row.__dict__ for row in rep.strong],
            use_container_width=True,
            hide_index=True,
        )
    if rep.thin:
        with st.expander(f"Thin-data guesses ({len(rep.thin)})"):
            st.dataframe(
                [row.__dict__ for row in rep.thin],
                use_container_width=True,
                hide_index=True,
            )


def _render_top_saved(doc: dict) -> None:
    st.caption(f"Last extracted · metric `{doc.get('metric')}`")
    st.markdown(doc.get("summary", ""))
    if doc.get("strong"):
        styling.section("Strong patterns")
        st.dataframe(doc["strong"], use_container_width=True, hide_index=True)
    if doc.get("thin"):
        with st.expander(f"Thin-data guesses ({len(doc['thin'])})"):
            st.dataframe(doc["thin"], use_container_width=True, hide_index=True)


def _render_losing(rep: losing_posts.LosingReport) -> None:
    st.markdown(rep.summary)
    if rep.rows:
        _losing_table([row.__dict__ for row in rep.rows])
    else:
        styling.empty_state("No losing rows", "No patterns emerged from the bottom N.")


def _render_losing_saved(doc: dict) -> None:
    st.caption(f"Last extracted · metric `{doc.get('metric')}`")
    st.markdown(doc.get("summary", ""))
    rows = doc.get("rows", [])
    if rows:
        _losing_table(rows)
    else:
        styling.empty_state("No losing rows", "No patterns emerged from the bottom N.")


def _losing_table(rows: list[dict]) -> None:
    styling.section("Candidates")
    st.dataframe(rows, use_container_width=True, hide_index=True)
