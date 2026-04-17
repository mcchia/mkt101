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

st.set_page_config(page_title="Tea Marketing Assistant", layout="wide")


def _sched_banner() -> None:
    try:
        cfg = scheduler.load_config()
        if scheduler.is_due(cfg):
            st.warning(
                "Scheduled sync is due. Open **Sync Scheduler** and click "
                "**Run now**, or run `python -m scripts.run_sync` from cron.",
                icon=":material/schedule:" if hasattr(st, "badge") else None,
            )
    except Exception:
        pass


def _page(fn, title: str, icon: str | None = None):
    return st.Page(fn, title=title, icon=icon)


nav = st.navigation(
    {
        "Workspace": [
            _page(chat.render, "Assistant"),
            _page(templates_page.render, "Templates"),
            _page(seasonal_page.render, "Seasonal Planner"),
            _page(ab_testing_page.render, "A/B Testing"),
        ],
        "Knowledge": [
            _page(brand_memory_page.render, "Brand Memory"),
            _page(content_history_page.render, "Content History"),
            _page(patterns_page.render, "Patterns & Losing Posts"),
        ],
        "Protection & ops": [
            _page(brand_protection_page.render, "Brand Protection"),
            _page(competitor_watch_page.render, "Competitor Watch"),
            _page(scheduler_page.render, "Sync Scheduler"),
        ],
    }
)

_sched_banner()
nav.run()
