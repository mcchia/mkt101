"""Idea Critique & Scoring page."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from models import IdeaStatus
from services.ideas import critique_and_score
from services.llm import LLMError
from services.scoring import brief_score_summary, rank_ideas
from storage import get_repository
from ui.components import status_badge


def render() -> None:
    st.header("Idea Critique & Scoring")
    st.caption(
        "Each idea gets scored on a 7-dimension rubric. "
        "Premium safety and brand fit are heavily weighted — ideas that threaten premium perception get penalized hard."
    )

    repo = get_repository()
    brand = repo.get_brand()
    ideas = repo.list_ideas()
    if not ideas:
        st.info("Generate ideas first.")
        return

    batches = sorted({i.batch_id for i in ideas if i.batch_id})
    default_batch = st.session_state.get("last_idea_batch") or (batches[-1] if batches else None)
    selected_batch = st.selectbox(
        "Batch",
        options=batches,
        index=batches.index(default_batch) if default_batch in batches else max(0, len(batches) - 1),
    )
    batch_ideas = [i for i in ideas if i.batch_id == selected_batch]

    unscored = [i for i in batch_ideas if i.score.total() == 0]
    cols = st.columns([3, 1])
    cols[0].caption(
        f"{len(batch_ideas)} ideas in batch · {len(unscored)} unscored · "
        f"{len([i for i in batch_ideas if i.score.total()>0])} scored"
    )
    if cols[1].button(
        "Critique & score",
        type="primary",
        use_container_width=True,
        disabled=not batch_ideas,
    ):
        recent_for_context = [i for i in ideas if i.batch_id != selected_batch][-40:]
        with st.spinner("Scoring…"):
            try:
                updated, usage = critique_and_score(batch_ideas, brand, recent_for_context)
            except LLMError as e:
                st.error(str(e))
                return
        for idea in updated:
            repo.save_idea(idea)
        st.session_state["critique_usage"] = {
            "in": usage.input_tokens,
            "out": usage.output_tokens,
            "cache_read": usage.cache_read,
            "cache_write": usage.cache_write,
        }
        st.success("Scored.")
        st.rerun()

    scored = [i for i in batch_ideas if i.score.total() > 0]
    if not scored:
        return

    ranked = rank_ideas(scored)

    st.markdown("#### Scored ideas (ranked)")
    for idea in ranked:
        with st.container(border=True):
            head = st.columns([3, 1, 1])
            head[0].markdown(f"**{idea.title}**  \n{idea.concept}")
            head[1].markdown(status_badge(idea.status), unsafe_allow_html=True)
            head[2].metric("score", f"{idea.score.total():.2f}")
            st.caption(brief_score_summary(idea.score))
            cols = st.columns(2)
            with cols[0]:
                st.markdown("**Upside**")
                st.write(idea.critique.likely_upside or "—")
            with cols[1]:
                st.markdown("**Weakness**")
                st.write(idea.critique.likely_weakness or "—")
            if idea.critique.risks:
                st.markdown("**Risks**")
                for r in idea.critique.risks:
                    st.markdown(f"- {r}")

            action_cols = st.columns(4)
            if action_cols[0].button("Edit notes", key=f"edit_{idea.id}"):
                st.session_state[f"edit_{idea.id}"] = True
            if action_cols[1].button("Reject", key=f"rej_{idea.id}"):
                idea.status = IdeaStatus.REJECTED
                repo.save_idea(idea)
                st.rerun()
            if action_cols[2].button("Shortlist (review)", key=f"short_{idea.id}"):
                idea.status = IdeaStatus.NEEDS_REVIEW
                repo.save_idea(idea)
                st.rerun()
            if action_cols[3].button("Delete", key=f"del_{idea.id}"):
                repo.delete_idea(idea.id)
                st.rerun()

            if st.session_state.get(f"edit_{idea.id}"):
                new_notes = st.text_area("Notes", value=idea.notes, key=f"notes_{idea.id}")
                if st.button("Save notes", key=f"save_notes_{idea.id}"):
                    idea.notes = new_notes
                    repo.save_idea(idea)
                    st.session_state.pop(f"edit_{idea.id}", None)
                    st.rerun()

    st.divider()
    st.markdown("#### Score matrix")
    df = pd.DataFrame(
        [
            {
                "title": i.title,
                "platform": i.platform,
                "format": i.format,
                "pillar": i.pillar,
                "brand_fit": i.score.brand_fit,
                "audience": i.score.audience_relevance,
                "engagement": i.score.engagement_potential,
                "conversion": i.score.conversion_support,
                "originality": i.score.originality,
                "ease": i.score.production_ease,
                "premium": i.score.premium_safety,
                "total": i.score.total(),
                "status": i.status.value,
            }
            for i in ranked
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
