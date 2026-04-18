"""Streamlit UI for the tea brand AI marketing assistant.

Multipage app. Each feature lives under `ui/pages/`. Legacy single-page chat
behavior is preserved by the "Assistant" page.

Usage:
    # Set ANTHROPIC_API_KEY via your environment, a local .env file, or
    # .streamlit/secrets.toml. Never hardcode or commit the key.
    streamlit run tea_assistant_ui.py
"""

from __future__ import annotations

import streamlit as st

from services import scheduler
from ui import styling
from ui.pages import (
    ab_testing_page,
    brand_memory_page,
    brand_protection_page,
    chat,
    competitor_watch_page,
    content_history_page,
    patterns_page,
    scheduler_page,
    seasonal_page,
    templates_page,
)

st.set_page_config(
    page_title="Tea Marketing Assistant",
    layout="wide",
    initial_sidebar_state="expanded",
)
styling.apply_theme()


def _sidebar_brand() -> None:
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 0.25rem 0 1rem 0; border-bottom: 1px solid var(--tea-line); margin-bottom: 1rem;">
                <div style="font-family: var(--tea-serif); font-size: 1.15rem; color: var(--tea-ink); font-weight: 600; letter-spacing: -0.005em;">
                    Tea Marketing
                </div>
                <div style="font-size: 0.78rem; color: var(--tea-muted); letter-spacing: 0.04em; text-transform: uppercase;">
                    Operations workspace
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _sched_banner() -> None:
    try:
        cfg = scheduler.load_config()
        if scheduler.is_due(cfg):
            st.info(
                "Scheduled sync is due. Open **Sync Scheduler** and click "
                "**Run now**, or run `python -m scripts.run_sync` from cron.",
                icon=":material/schedule:",
            )
    except Exception:
        pass


def _page(fn, title: str, url_path: str, icon: str | None = None):
    return st.Page(fn, title=title, url_path=url_path, icon=icon)


_sidebar_brand()

nav = st.navigation(
    {
        "Workspace": [
            _page(chat.render, "Assistant", "assistant", icon=":material/auto_awesome:"),
            _page(templates_page.render, "Templates", "templates", icon=":material/dashboard_customize:"),
            _page(seasonal_page.render, "Seasonal Planner", "seasonal", icon=":material/calendar_month:"),
            _page(ab_testing_page.render, "A/B Testing", "ab-testing", icon=":material/compare_arrows:"),
        ],
        "Knowledge": [
            _page(brand_memory_page.render, "Brand Memory", "brand-memory", icon=":material/bookmark:"),
            _page(content_history_page.render, "Content History", "content-history", icon=":material/history:"),
            _page(patterns_page.render, "Patterns & Losing Posts", "patterns", icon=":material/insights:"),
        ],
        "Protection & ops": [
            _page(brand_protection_page.render, "Brand Protection", "brand-protection", icon=":material/shield:"),
            _page(competitor_watch_page.render, "Competitor Watch", "competitor-watch", icon=":material/visibility:"),
            _page(scheduler_page.render, "Sync Scheduler", "scheduler", icon=":material/schedule:"),
        ],
    }
)

_sched_banner()
nav.run()
