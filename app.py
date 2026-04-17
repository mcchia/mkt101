"""Streamlit entry point. Run with: `streamlit run app.py`.

Loads .env, wires up navigation, and renders the sidebar. Every page lives in
`ui/pages/*.py` and exposes a `render()` function — this file stays tiny.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path when Streamlit launches app.py
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env", override=False)
except ImportError:
    pass

import streamlit as st  # noqa: E402

from ui.sidebar import render_sidebar  # noqa: E402
from ui.pages import (  # noqa: E402
    brand_profile,
    calendar as calendar_page,
    critique,
    data_sources,
    ideas,
    logs,
    overview,
    performance,
    sop,
    top3,
)


st.set_page_config(
    page_title="mkt101 — tea brand marketing operator",
    layout="wide",
    initial_sidebar_state="expanded",
)


PAGES = [
    ("Overview", overview.render),
    ("Brand Profile", brand_profile.render),
    ("Data Sources", data_sources.render),
    ("Performance Analysis", performance.render),
    ("Idea Generation", ideas.render),
    ("Idea Critique & Scoring", critique.render),
    ("Top 3 Recommendations", top3.render),
    ("Content Calendar", calendar_page.render),
    ("SOP / Dashboard Logic", sop.render),
    ("Sync / Logs / Status", logs.render),
]


def main() -> None:
    render_sidebar()

    st.sidebar.divider()
    st.sidebar.markdown("**Navigation**")

    labels = [name for name, _ in PAGES]
    default = st.session_state.get("current_page", labels[0])
    selected = st.sidebar.radio(
        "Workflow",
        options=labels,
        index=labels.index(default) if default in labels else 0,
        label_visibility="collapsed",
    )
    st.session_state["current_page"] = selected

    render_fn = dict(PAGES)[selected]
    render_fn()


if __name__ == "__main__":
    main()
