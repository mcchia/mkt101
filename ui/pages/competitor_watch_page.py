"""Competitor Watch page."""

from __future__ import annotations

import streamlit as st

from connectors.competitors import manual, web
from services import competitor_watch


def render() -> None:
    st.title("Competitor Watch")
    st.caption(
        "Track competitors to understand the landscape without copying them. "
        "Manual entries are the default. Optional safe public-web fetches stay "
        "conservative: single request per action, no scraping loops."
    )

    tab_setup, tab_observe, tab_insights = st.tabs(["Setup", "Observations", "Insights"])

    with tab_setup:
        with st.form("comp_form"):
            name = st.text_input("Name")
            handles_raw = st.text_area(
                "Handles (one per line, e.g. @brand_ig, fb:BrandPage)",
                height=90,
            )
            urls_raw = st.text_area(
                "Public URLs (one per line, https only, avoid URLs with tracking query strings)",
                height=90,
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
        if competitors:
            st.subheader("Saved competitors")
            for c in competitors:
                with st.expander(c.name):
                    st.markdown(f"**Handles:** {', '.join(c.handles) or '—'}")
                    st.markdown(f"**URLs:** {', '.join(c.urls) or '—'}")
                    if c.notes:
                        st.markdown(f"**Notes:** {c.notes}")
                    if st.button("Delete", key=f"del-comp-{c.id}"):
                        manual.delete(c.id)
                        st.rerun()

    with tab_observe:
        competitors = manual.list_competitors()
        if not competitors:
            st.info("Add a competitor first.")
            return
        pick = st.selectbox(
            "Competitor",
            options=[c.id for c in competitors],
            format_func=lambda cid: next((c.name for c in competitors if c.id == cid), cid),
        )
        sub_manual, sub_web = st.tabs(["Log manual observation", "Fetch public URL"])

        with sub_manual:
            with st.form("obs_form"):
                themes = st.text_area("Themes (one per line)", height=90)
                frequency = st.text_input("Posting frequency", placeholder="3-4x/week")
                offer_style = st.text_input("Offer style", placeholder="bundle pricing, gift with purchase")
                visuals = st.text_area("Visual patterns", height=80)
                angles = st.text_area("Recurring campaign angles (one per line)", height=80)
                if st.form_submit_button("Add observation"):
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
                "Fetches a single public HTML page with a short timeout and size "
                "cap. Uses `robots.txt` politely. No cookies or auth are sent."
            )
            comp = next((c for c in competitors if c.id == pick), None)
            url = st.selectbox("URL", options=(comp.urls if comp else [])) if comp and comp.urls else st.text_input("URL (https)")
            if st.button("Fetch now"):
                try:
                    obs = competitor_watch.capture_web_observation(pick, url)
                    st.success(f"Observation captured from {obs.get('source_url', url)}")
                except web.CompetitorFetchError as e:
                    st.error(f"Fetch refused: {e}")
                except Exception:
                    st.error("Unexpected error while fetching. Check your URL or try again later.")

        st.divider()
        current = next((c for c in competitors if c.id == pick), None)
        if current and current.observations:
            st.subheader("Observations log")
            for obs in reversed(current.observations[-20:]):
                with st.expander(f"{obs.get('source', '?')} · {obs.get('offer_style', '') or '—'}"):
                    st.json(obs)

    with tab_insights:
        if not manual.list_competitors():
            st.info("Add competitors first.")
            return
        scope = st.radio("Scope", ["All competitors", "Single competitor"], horizontal=True)
        target = None
        if scope == "Single competitor":
            comps = manual.list_competitors()
            target = st.selectbox(
                "Competitor",
                options=[c.id for c in comps],
                format_func=lambda cid: next((c.name for c in comps if c.id == cid), cid),
            )
        if st.button("Synthesize insights", type="primary"):
            with st.spinner("Synthesizing..."):
                try:
                    insights = competitor_watch.synthesize_insights(target)
                except Exception as e:
                    st.error(f"Could not synthesize: {e}")
                else:
                    st.markdown(f"**Summary:** {insights.get('competitor_summary', '')}")
                    if insights.get("crowded_themes"):
                        st.subheader("Crowded themes")
                        for t in insights["crowded_themes"]:
                            st.markdown(f"- {t}")
                    if insights.get("themes"):
                        st.subheader("Themes")
                        st.write(insights["themes"])
                    if insights.get("whitespace_opportunities"):
                        st.subheader("Whitespace opportunities")
                        for w in insights["whitespace_opportunities"]:
                            if isinstance(w, dict):
                                st.markdown(
                                    f"- **{w.get('opportunity', '')}** — "
                                    f"{w.get('why_it_fits_us', '')} "
                                    f"_risk:_ {w.get('risk', '')}"
                                )
                            else:
                                st.markdown(f"- {w}")
                    if insights.get("do_not_copy_notes"):
                        st.caption("Do not copy: " + insights["do_not_copy_notes"])
