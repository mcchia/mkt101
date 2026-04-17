"""Idea Generation page."""
from __future__ import annotations

import streamlit as st

from services.ideas import generate_ideas
from services.llm import LLMError
from storage import get_repository
from ui.components import render_idea_card


def render() -> None:
    st.header("Idea Generation")
    st.caption(
        "Generates 10–15 distinct next-post ideas, grounded in the most recent analysis "
        "and brand memory. Nothing is scored here yet — scoring happens on the next page."
    )

    repo = get_repository()
    brand = repo.get_brand()
    ideas_existing = repo.list_ideas()
    analysis = st.session_state.get("analysis")

    if not analysis:
        st.info(
            "Run **Performance Analysis** first — idea generation uses it as the justification ground truth."
        )
        return

    st.caption(
        f"{len(ideas_existing)} ideas stored. Last analysis at "
        f"{st.session_state.get('analysis_at','?')}."
    )

    goal = st.session_state.get("analysis_goal", "")
    cols = st.columns([3, 1])
    with cols[0]:
        st.text_input("Goal context (read-only — set on Analysis page)", value=goal, disabled=True)
    with cols[1]:
        clear = st.checkbox("Replace existing ideas", value=False)

    if st.button("Generate ideas", type="primary", use_container_width=True):
        with st.spinner("Generating…"):
            try:
                new_ideas, usage = generate_ideas(analysis, brand, ideas_existing, goal)
            except LLMError as e:
                st.error(str(e))
                return
        if clear:
            for old in ideas_existing:
                repo.delete_idea(old.id)
        repo.add_ideas(new_ideas)
        st.session_state["last_idea_batch"] = new_ideas[0].batch_id if new_ideas else None
        st.session_state["ideas_usage"] = {
            "in": usage.input_tokens,
            "out": usage.output_tokens,
            "cache_read": usage.cache_read,
            "cache_write": usage.cache_write,
        }
        st.success(f"Generated {len(new_ideas)} ideas.")
        st.rerun()

    batch_id = st.session_state.get("last_idea_batch")
    latest = [i for i in repo.list_ideas() if i.batch_id == batch_id] if batch_id else repo.list_ideas()
    if not latest:
        return

    st.markdown(f"#### Latest batch ({len(latest)} ideas)")
    for idea in latest:
        render_idea_card(idea)
