"""A/B Testing page."""

from __future__ import annotations

import streamlit as st

from services import ab_testing
from ui import styling


def render() -> None:
    styling.page_header(
        "A/B Testing",
        subtitle=(
            "Generate two on-brand variants for a selected concept. Only the "
            "named dimension changes between A and B."
        ),
        eyebrow="Workspace",
    )

    with styling.card():
        st.markdown("**New A/B plan**")
        with st.form("ab_form"):
            concept = st.text_area(
                "Concept",
                height=140,
                placeholder="Paste the idea or the top-3 pick here.",
            )
            col_dim, col_ctx = st.columns([1, 2])
            with col_dim:
                dimension = st.selectbox("Dimension to vary", ab_testing.DIMENSIONS)
            with col_ctx:
                context = st.text_input(
                    "Optional context",
                    placeholder="KPI hypothesis, audience slice…",
                )
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

    styling.section("Saved A/B plans", subtitle="Most recent first.")
    plans = ab_testing.list_plans()
    if not plans:
        styling.empty_state(
            "No plans yet",
            "Generate a new plan above. Plans are persisted locally for reference.",
        )
        return
    for plan in reversed(plans):
        header = f"{plan.get('dimension', '?')} · {plan.get('concept', '')[:80]}"
        with st.expander(header):
            _render_plan(plan)
            if st.button("Delete", key=f"del-ab-{plan['id']}"):
                ab_testing.delete_plan(plan["id"])
                st.rerun()


def _render_plan(plan: dict) -> None:
    body = plan.get("plan", {}) if isinstance(plan.get("plan"), dict) else plan
    styling.kv_list(
        [
            ("Dimension", str(body.get("dimension", plan.get("dimension", "—")))),
            ("What is changing", str(body.get("what_is_changing", ""))),
            ("KPI to learn from", str(body.get("kpi", ""))),
        ]
    )

    col_a, col_b = st.columns(2)
    for col, key, label in [(col_a, "variant_a", "Variant A"), (col_b, "variant_b", "Variant B")]:
        with col:
            with styling.card():
                st.markdown(
                    f"<div style='font-family:var(--tea-serif);"
                    f"font-size:1.05rem;color:var(--tea-ink);"
                    f"margin-bottom:0.5rem;font-weight:600;'>{label}</div>",
                    unsafe_allow_html=True,
                )
                var = body.get(key, {})
                if not isinstance(var, dict):
                    st.text(str(var))
                    continue
                for field in ("hook", "caption", "format", "cta"):
                    if var.get(field):
                        st.markdown(
                            f"<div style='font-size:0.78rem;color:var(--tea-muted);"
                            f"text-transform:uppercase;letter-spacing:0.06em;"
                            f"margin-top:0.5rem;'>{field}</div>"
                            f"<div style='color:var(--tea-ink);'>{var[field]}</div>",
                            unsafe_allow_html=True,
                        )
    notes = body.get("guardrail_notes")
    if notes:
        st.caption(f"Guardrails: {notes}")
