"""Sidebar with brand snapshot, data source status, LLM key status."""
from __future__ import annotations

import streamlit as st

from config import get_settings
from models import SyncStatus
from storage import get_repository
from ui.components import freshness_label


def render_sidebar() -> None:
    settings = get_settings()
    repo = get_repository()

    st.sidebar.markdown("### mkt101")
    st.sidebar.caption("Premium tea brand marketing operator")

    st.sidebar.divider()

    # LLM status
    if settings.anthropic_api_key:
        st.sidebar.success("LLM key: loaded", icon="✅")
    else:
        st.sidebar.error("LLM key: missing", icon="⚠️")
        st.sidebar.caption("Set `ANTHROPIC_API_KEY` in .env")

    st.sidebar.caption(f"Model: `{settings.model}`")

    st.sidebar.divider()

    # Brand summary
    st.sidebar.markdown("**Brand**")
    brand = repo.get_brand()
    if brand and brand.brand_name:
        st.sidebar.write(brand.brand_name)
        if brand.one_liner:
            st.sidebar.caption(brand.one_liner)
        st.sidebar.caption(
            f"{len(brand.content_pillars)} pillars · "
            f"{brand.posting_constraints.max_posts_per_week}/wk cap"
        )
    else:
        st.sidebar.caption("Brand profile not yet set — open *Brand Profile*.")

    st.sidebar.divider()

    # Data freshness
    st.sidebar.markdown("**Data**")
    posts = repo.list_posts()
    syncs = repo.list_syncs()
    st.sidebar.caption(f"{len(posts)} post records stored")
    last_ok = next(
        (s for s in reversed(syncs) if s.status in (SyncStatus.OK, SyncStatus.PARTIAL)),
        None,
    )
    if last_ok:
        st.sidebar.caption(
            f"Last sync ({last_ok.source.value}): {freshness_label(last_ok.finished_at or last_ok.started_at)}"
        )
    else:
        st.sidebar.caption("No successful sync yet.")

    # Meta creds presence
    st.sidebar.divider()
    st.sidebar.markdown("**Meta Graph**")
    if settings.meta_access_token:
        st.sidebar.caption("Token: ✓")
    else:
        st.sidebar.caption("Token: —")
    st.sidebar.caption(f"FB page: {'✓' if settings.meta_fb_page_id else '—'}")
    st.sidebar.caption(f"IG user: {'✓' if settings.meta_ig_user_id else '—'}")

    st.sidebar.divider()
    if settings.allow_autopost:
        st.sidebar.warning("Autopost enabled (env flag)")
    else:
        st.sidebar.caption("Autopost: off (approval-first)")
