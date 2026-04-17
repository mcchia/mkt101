"""A/B Testing page."""

from __future__ import annotations

import streamlit as st

from services import ab_testing


def render() -> None:
    st.title("A/B Testing")
    st.caption(
        "Generate two on-brand variants for a selected concept. Only the named "
        "dimension changes between A and B."
    )

    with st.form("ab_form"):
        concept = st.text_area("Concept", height=120, placeholder="Paste the idea / top-3 pick here.")
        dimension = st.selectbox("Dimension to vary", ab_testing.DIMENSIONS)
        context = st.text_area("Optional context (KPI hypothesis, audience slice, etc.)", height=80)
        submitted = st.form_submit_button("Generate variants", type="primary")

    if submitted:
        if not concept.strip():
            st.error("Concept is required.")
        else:
            with st.spinner("Generating A/B variants..."):
                try:
                    plan = ab_testing.generate_plan(concept, dimension, context)
                    st.success("Saved.")
                    _render_plan(plan)
                except Exception as e:
                    st.error(f"Could not generate: {e}")

    st.divider()
    st.subheader("Saved A/B plans")
    plans = ab_testing.list_plans()
    if not plans:
        st.info("No saved plans yet.")
        return
    for plan in reversed(plans):
        with st.expander(f"{plan.get('dimension', '?')} · {plan.get('concept', '')[:80]}"):
            _render_plan(plan)
            if st.button("Delete", key=f"del-ab-{plan['id']}"):
                ab_testing.delete_plan(plan["id"])
                st.rerun()


def _render_plan(plan: dict) -> None:
    body = plan.get("plan", {}) if isinstance(plan.get("plan"), dict) else plan
    st.markdown(f"**Dimension:** {body.get('dimension', plan.get('dimension', '?'))}")
    st.markdown(f"**What is changing:** {body.get('what_is_changing', '')}")
    st.markdown(f"**KPI to learn from:** {body.get('kpi', '')}")
    col_a, col_b = st.columns(2)
    for col, key, label in [(col_a, "variant_a", "Variant A"), (col_b, "variant_b", "Variant B")]:
        with col:
            st.subheader(label)
            var = body.get(key, {})
            if not isinstance(var, dict):
                st.text(str(var))
                continue
            for field in ("hook", "caption", "format", "cta"):
                if var.get(field):
                    st.markdown(f"**{field.title()}:** {var[field]}")
    notes = body.get("guardrail_notes")
    if notes:
        st.caption(f"Guardrails: {notes}")
