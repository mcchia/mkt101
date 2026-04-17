"""Patterns + losing posts page."""

from __future__ import annotations

import streamlit as st

from services import losing_posts, patterns


def render() -> None:
    st.title("Patterns & Losing Posts")
    st.caption(
        "Extract patterns from winners and losers in your content history. "
        "Weak-evidence patterns are separated from strong ones."
    )

    metric = st.selectbox("Winning metric", patterns.AVAILABLE_METRICS, index=patterns.AVAILABLE_METRICS.index("weighted"))
    col1, col2 = st.columns(2)
    with col1:
        top_n = st.slider("Top N (winners)", 3, 20, 5)
    with col2:
        bottom_n = st.slider("Bottom N (losers)", 3, 20, 5)

    run = st.button("Run extraction", type="primary")

    tab_top, tab_lose = st.tabs(["Winners", "Losers"])

    with tab_top:
        if run:
            rep = patterns.extract(metric=metric, top_n=top_n)
            _render_top(rep)
        else:
            doc = patterns.last_saved_summary()
            if doc:
                st.caption(f"Last extracted at ts={doc.get('generated_at')} · metric={doc.get('metric')}")
                st.write(doc.get("summary", ""))
                if doc.get("strong"):
                    st.subheader("Strong patterns")
                    st.dataframe(doc["strong"])
                if doc.get("thin"):
                    with st.expander("Thin-data guesses"):
                        st.dataframe(doc["thin"])
            else:
                st.info("Run extraction to see winning patterns.")

    with tab_lose:
        if run:
            rep = losing_posts.extract(metric=metric, bottom_n=bottom_n)
            _render_losing(rep)
        else:
            doc = losing_posts.last_saved_summary()
            if doc:
                st.caption(f"Last extracted at ts={doc.get('generated_at')} · metric={doc.get('metric')}")
                st.write(doc.get("summary", ""))
                if doc.get("rows"):
                    st.dataframe(doc["rows"])
            else:
                st.info("Run extraction to see losing patterns.")


def _render_top(rep: patterns.PatternReport) -> None:
    st.write(rep.summary)
    if rep.strong:
        st.subheader("Strong patterns")
        st.dataframe([row.__dict__ for row in rep.strong])
    if rep.thin:
        with st.expander("Thin-data guesses"):
            st.dataframe([row.__dict__ for row in rep.thin])


def _render_losing(rep: losing_posts.LosingReport) -> None:
    st.write(rep.summary)
    if rep.rows:
        st.dataframe([row.__dict__ for row in rep.rows])
    else:
        st.info("No losing rows.")
