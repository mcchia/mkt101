"""Seasonal planner page."""

from __future__ import annotations

import json

import streamlit as st

from services import seasonal_planner


def render() -> None:
    st.title("Seasonal Planner")
    st.caption(
        "Calendar-aware plans for Tet, Mid-Autumn, corporate gifting, holiday "
        "gift boxes, and wellness windows. Respects premium guardrails."
    )

    with st.form("season_form"):
        season_key = st.selectbox(
            "Season",
            options=list(seasonal_planner.SEASON_PRESETS.keys()),
            format_func=lambda k: seasonal_planner.SEASON_PRESETS[k]["label"],
        )
        preset = seasonal_planner.SEASON_PRESETS[season_key]
        st.caption(f"Typical window: {preset['typical_window']}")
        objective = st.text_area("Objective", height=80, placeholder="e.g. drive premium gift-box orders before Tet week")
        window = st.text_input("Timing window (actual)", placeholder=preset["typical_window"])
        audience = st.text_input("Audience", placeholder="e.g. urban gift-buyers, 28-45, Hanoi and HCMC")
        product_focus = st.text_input("Product focus (optional)")
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

    st.divider()
    st.subheader("Saved plans")
    plans = seasonal_planner.list_plans()
    if not plans:
        st.info("No plans yet.")
        return
    for plan in reversed(plans):
        with st.expander(f"{plan.season_label} · {plan.objective[:60]}"):
            _render_plan(plan)
            if st.button("Delete", key=f"del-plan-{plan.id}"):
                seasonal_planner.delete_plan(plan.id)
                st.rerun()


def _render_plan(plan: seasonal_planner.SeasonalPlan) -> None:
    st.markdown(f"**Objective:** {plan.objective}")
    st.markdown(f"**Window:** {plan.timing_window}")
    st.markdown(f"**Audience:** {plan.audience}")
    if plan.product_focus:
        st.markdown(f"**Product focus:** {plan.product_focus}")
    body = plan.plan or {}
    if body.get("headline_narrative"):
        st.markdown(f"**Narrative:** {body['headline_narrative']}")
    timeline = body.get("timeline") or []
    if timeline:
        st.subheader("Timeline")
        for phase in timeline:
            if not isinstance(phase, dict):
                continue
            st.markdown(f"**{phase.get('phase', '?')}** · {phase.get('window', '')} · focus: {phase.get('focus', '')}")
            for post in phase.get("posts", []) or []:
                if not isinstance(post, dict):
                    continue
                st.markdown(
                    f"- [{post.get('channel', '?')} · {post.get('format', '?')}] "
                    f"**hook:** {post.get('hook', '')}  \n"
                    f"  angle: {post.get('angle', '')} · cta: {post.get('cta', '')} · "
                    f"pillar: {post.get('pillar', '')} · kpi: {post.get('kpi', '')}"
                )
    if body.get("risks_to_avoid"):
        st.subheader("Risks to avoid")
        for r in body["risks_to_avoid"]:
            st.markdown(f"- {r}")
    if body.get("connect_to_calendar_notes"):
        st.caption(f"Calendar notes: {body['connect_to_calendar_notes']}")
    with st.expander("Raw JSON"):
        st.code(json.dumps(body, ensure_ascii=False, indent=2), language="json")
