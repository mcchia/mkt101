"""SOP / dashboard logic page."""
from __future__ import annotations

import json

import streamlit as st

from services.llm import LLMError
from services.sop import generate_sop_and_dashboard
from storage import get_repository


def render() -> None:
    st.header("SOP & Dashboard Logic")
    st.caption(
        "Weekly operating procedure and the exact questions your dashboard should answer. "
        "Grounded in the current analysis and top-3 decisions."
    )

    repo = get_repository()
    brand = repo.get_brand()
    analysis = st.session_state.get("analysis")
    ideas = repo.list_ideas()
    top3 = [i for i in ideas if i.selected_top3]

    if not analysis:
        st.info("Run performance analysis first.")
        return

    if st.button(
        "Generate SOP + dashboard recommendations",
        type="primary",
        use_container_width=True,
    ):
        with st.spinner("Writing…"):
            try:
                data, usage = generate_sop_and_dashboard(analysis, top3, brand)
            except LLMError as e:
                st.error(str(e))
                return
        st.session_state["sop"] = data
        st.session_state["sop_usage"] = {
            "in": usage.input_tokens,
            "out": usage.output_tokens,
            "cache_read": usage.cache_read,
            "cache_write": usage.cache_write,
        }
        st.rerun()

    sop = st.session_state.get("sop")
    if not sop:
        return

    st.markdown("### Weekly SOP")
    for step in sop.get("weekly_sop", []):
        st.markdown(
            f"- **{step.get('day','?')}** — {step.get('step','')} "
            f"_(owner: {step.get('owner','?')}; output: {step.get('output','?')})_"
        )

    st.markdown("### Dashboard questions")
    for q in sop.get("dashboard_questions", []):
        st.markdown(
            f"- **{q.get('question','')}** — metric: `{q.get('metric','')}` — {q.get('reading_guide','')}"
        )

    cols = st.columns(3)
    with cols[0]:
        st.markdown("### Repeat")
        for item in sop.get("repeat", []):
            st.markdown(f"- {item}")
    with cols[1]:
        st.markdown("### Stop")
        for item in sop.get("stop", []):
            st.markdown(f"- {item}")
    with cols[2]:
        st.markdown("### Test next")
        for item in sop.get("test_next", []):
            st.markdown(f"- {item}")

    st.divider()
    st.download_button(
        "Download SOP JSON",
        data=json.dumps(sop, indent=2, ensure_ascii=False).encode("utf-8"),
        file_name="sop.json",
        mime="application/json",
    )
