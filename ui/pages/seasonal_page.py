"""Seasonal planner page."""

from __future__ import annotations

import json

import streamlit as st

from services import seasonal_planner
from ui import styling


def render() -> None:
    styling.page_header(
        "Seasonal Planner",
        subtitle=(
            "Calendar-aware plans for Tet, Mid-Autumn, corporate gifting, "
            "holiday gift boxes, and wellness windows. Respects premium "
            "guardrails."
        ),
        eyebrow="Workspace",
    )

    with styling.card():
        st.markdown("**New seasonal plan**")
        with st.form("season_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                season_key = st.selectbox(
                    "Season",
                    options=list(seasonal_planner.SEASON_PRESETS.keys()),
                    format_func=lambda k: seasonal_planner.SEASON_PRESETS[k]["label"],
                )
                preset = seasonal_planner.SEASON_PRESETS[season_key]
                st.caption(f"Typical window: {preset['typical_window']}")
                window = st.text_input(
                    "Actual timing window",
                    placeholder=preset["typical_window"],
                )
            with col_b:
                audience = st.text_input(
                    "Audience",
                    placeholder="e.g. urban gift-buyers, 28–45",
                )
                product_focus = st.text_input("Product focus (optional)")
            objective = st.text_area(
                "Objective",
                height=90,
                placeholder="e.g. drive premium gift-box orders before Tet week",
            )
            submitted = st.form_submit_button("Generate plan", type="primary")

    if submitted:
        if not objective.strip() or not audience.strip():
            st.error("Objective and audience are required.")
        else:
            with st.spinner("Generating plan..."):
                try:
                    plan = seasonal_planner.generate_plan(
                        season_key,
                        objective=objective,
                        timing_window=window,
                        audience=audience,
                        product_focus=product_focus,
                    )
                    st.success(f"Saved: {plan.season_label}")
                    _render_plan(plan)
                except Exception as e:
                    st.error(f"Could not generate: {e}")

    styling.section("Saved plans", "Most recent first.")
    plans = seasonal_planner.list_plans()
    if not plans:
        styling.empty_state(
            "No plans yet",
            "Generate a plan above. Plans are persisted locally for reference.",
        )
        return
    for plan in reversed(plans):
        with st.expander(f"{plan.season_label} · {plan.objective[:60]}"):
            _render_plan(plan)
            if st.button("Delete", key=f"del-plan-{plan.id}"):
                seasonal_planner.delete_plan(plan.id)
                st.rerun()


def _render_plan(plan: seasonal_planner.SeasonalPlan) -> None:
    styling.kv_list(
        [
            ("Season", plan.season_label),
            ("Window", plan.timing_window),
            ("Audience", plan.audience),
            ("Objective", plan.objective),
            ("Product focus", plan.product_focus),
        ]
    )
    body = plan.plan or {}
    if body.get("headline_narrative"):
        styling.quote(body["headline_narrative"])

    timeline = body.get("timeline") or []
    if timeline:
        styling.section("Timeline")
        for phase in timeline:
            if not isinstance(phase, dict):
                continue
            with styling.card():
                st.markdown(
                    f"{styling.badge_html(str(phase.get('phase', '?')), 'info')}&nbsp;&nbsp;"
                    f"<span style='color:var(--tea-muted);font-size:0.85rem;'>"
                    f"{phase.get('window', '')}</span>",
                    unsafe_allow_html=True,
                )
                if phase.get("focus"):
                    st.markdown(f"**Focus:** {phase['focus']}")
                for post in phase.get("posts", []) or []:
                    if not isinstance(post, dict):
                        continue
                    channel = post.get("channel", "?")
                    fmt = post.get("format", "?")
                    st.markdown(
                        f"<div style='padding:0.4rem 0;border-top:1px solid var(--tea-line-soft);margin-top:0.4rem;'>"
                        f"{styling.badge_html(channel, 'neutral')} "
                        f"{styling.badge_html(fmt, 'neutral')}"
                        f"<div style='margin-top:0.3rem;color:var(--tea-ink);'>"
                        f"<strong>Hook:</strong> {post.get('hook', '')}</div>"
                        f"<div style='color:var(--tea-ink-soft);font-size:0.88rem;'>"
                        f"angle: {post.get('angle', '')} · cta: {post.get('cta', '')} · "
                        f"pillar: {post.get('pillar', '')} · kpi: {post.get('kpi', '')}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

    if body.get("risks_to_avoid"):
        styling.section("Risks to avoid")
        for r in body["risks_to_avoid"]:
            st.markdown(f"- {r}")
    if body.get("connect_to_calendar_notes"):
        st.caption(f"Calendar notes: {body['connect_to_calendar_notes']}")
    with st.expander("Raw JSON"):
        st.code(json.dumps(body, ensure_ascii=False, indent=2), language="json")
