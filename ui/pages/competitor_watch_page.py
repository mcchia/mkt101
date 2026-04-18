"""Competitor Watch page."""

from __future__ import annotations

import streamlit as st

from connectors.competitors import manual, web
from services import competitor_watch
from ui import styling


def render() -> None:
    styling.page_header(
        "Competitor Watch",
        subtitle=(
            "Track competitors to understand the landscape without copying "
            "them. Manual entries are the default. Optional public-web fetches "
            "stay conservative: single request, short timeout, no scraping loops."
        ),
        eyebrow="Protection & ops",
    )

    tab_setup, tab_observe, tab_insights = st.tabs(["Setup", "Observations", "Insights"])

    with tab_setup:
        with styling.card():
            st.markdown("**Add or update a competitor**")
            with st.form("comp_form"):
                name = st.text_input("Name")
                col_a, col_b = st.columns(2)
                with col_a:
                    handles_raw = st.text_area(
                        "Handles (one per line)",
                        placeholder="@brand_ig\nfb:BrandPage",
                        height=100,
                    )
                with col_b:
                    urls_raw = st.text_area(
                        "Public URLs (https only)",
                        placeholder="https://example.com/about",
                        height=100,
                    )
                notes = st.text_area("Notes", height=80)
                if st.form_submit_button("Save competitor", type="primary"):
                    try:
                        manual.upsert(
                            name=name,
                            handles=[h.strip() for h in handles_raw.splitlines() if h.strip()],
                            urls=[u.strip() for u in urls_raw.splitlines() if u.strip()],
                            notes=notes,
                        )
                        st.success("Saved.")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

        competitors = manual.list_competitors()
        styling.section("Saved competitors", f"{len(competitors)} on file")
        if not competitors:
            styling.empty_state(
                "No competitors yet",
                "Add at least one to unlock observations and insights.",
            )
        for c in competitors:
            with st.expander(f"{c.name}"):
                styling.kv_list(
                    [
                        ("Handles", ", ".join(c.handles)),
                        ("URLs", ", ".join(c.urls)),
                    ]
                )
                if c.notes:
                    styling.quote(c.notes)
                if st.button("Delete", key=f"del-comp-{c.id}"):
                    manual.delete(c.id)
                    st.rerun()

    with tab_observe:
        competitors = manual.list_competitors()
        if not competitors:
            styling.empty_state("Add a competitor first", "You can log observations once a competitor is on file.")
            return
        pick = st.selectbox(
            "Competitor",
            options=[c.id for c in competitors],
            format_func=lambda cid: next((c.name for c in competitors if c.id == cid), cid),
        )
        sub_manual, sub_web = st.tabs(["Log manual observation", "Fetch public URL"])

        with sub_manual:
            with st.form("obs_form"):
                col_a, col_b = st.columns(2)
                with col_a:
                    themes = st.text_area("Themes (one per line)", height=100)
                    frequency = st.text_input("Posting frequency", placeholder="3–4x / week")
                    offer_style = st.text_input(
                        "Offer style",
                        placeholder="bundle pricing, gift with purchase",
                    )
                with col_b:
                    visuals = st.text_area("Visual patterns", height=100)
                    angles = st.text_area("Recurring campaign angles (one per line)", height=100)
                if st.form_submit_button("Add observation", type="primary"):
                    manual.add_observation(
                        pick,
                        themes=[t.strip() for t in themes.splitlines() if t.strip()],
                        frequency=frequency,
                        offer_style=offer_style,
                        visual_patterns=visuals,
                        campaign_angles=[a.strip() for a in angles.splitlines() if a.strip()],
                        source="manual",
                    )
                    st.success("Observation added.")
                    st.rerun()

        with sub_web:
            st.caption(
                "Fetches a single public HTML page with a short timeout and "
                "size cap. Respects robots.txt. No cookies or auth headers are sent."
            )
            comp = next((c for c in competitors if c.id == pick), None)
            if comp and comp.urls:
                url = st.selectbox("URL", options=comp.urls)
            else:
                url = st.text_input("URL (https)")
            if st.button("Fetch now", type="primary"):
                try:
                    obs = competitor_watch.capture_web_observation(pick, url)
                    st.success(f"Observation captured from {obs.get('source_url', url)}")
                except web.CompetitorFetchError as e:
                    st.error(f"Fetch refused: {e}")
                except Exception:
                    st.error("Unexpected error while fetching. Check your URL or try again later.")

        styling.section("Observations log")
        current = next((c for c in competitors if c.id == pick), None)
        if not current or not current.observations:
            styling.empty_state("No observations yet", "Log one manually or fetch a public URL.")
        else:
            for obs in reversed(current.observations[-20:]):
                with st.expander(f"{obs.get('source', '?')} · {obs.get('offer_style', '') or '—'}"):
                    st.json(obs)

    with tab_insights:
        if not manual.list_competitors():
            styling.empty_state("Add competitors first", "Insights need at least one competitor on file.")
            return
        with styling.card():
            scope = st.radio("Scope", ["All competitors", "Single competitor"], horizontal=True)
            target = None
            if scope == "Single competitor":
                comps = manual.list_competitors()
                target = st.selectbox(
                    "Competitor",
                    options=[c.id for c in comps],
                    format_func=lambda cid: next((c.name for c in comps if c.id == cid), cid),
                )
            run = st.button("Synthesize insights", type="primary")

        if not run:
            return
        with st.spinner("Synthesizing..."):
            try:
                insights = competitor_watch.synthesize_insights(target)
            except Exception as e:
                st.error(f"Could not synthesize: {e}")
                return

        st.markdown(insights.get("competitor_summary", ""))

        col1, col2 = st.columns(2)
        with col1:
            styling.section("Crowded themes")
            crowded = insights.get("crowded_themes") or []
            if crowded:
                for t in crowded:
                    st.markdown(f"- {t}")
            else:
                st.caption("—")
        with col2:
            styling.section("Themes observed")
            themes = insights.get("themes") or []
            if themes:
                st.markdown(
                    " ".join(styling.badge_html(str(t), "neutral") for t in themes),
                    unsafe_allow_html=True,
                )
            else:
                st.caption("—")

        whitespace = insights.get("whitespace_opportunities") or []
        if whitespace:
            styling.section("Whitespace opportunities", "Angles under-served by the competitor set.")
            for w in whitespace:
                with styling.card():
                    if isinstance(w, dict):
                        st.markdown(f"**{w.get('opportunity', '')}**")
                        if w.get("why_it_fits_us"):
                            st.markdown(
                                f"<div style='color:var(--tea-ink-soft);'>"
                                f"{w['why_it_fits_us']}</div>",
                                unsafe_allow_html=True,
                            )
                        if w.get("risk"):
                            st.caption(f"Risk: {w['risk']}")
                    else:
                        st.markdown(f"- {w}")
        if insights.get("do_not_copy_notes"):
            st.caption(f"Do not copy: {insights['do_not_copy_notes']}")
