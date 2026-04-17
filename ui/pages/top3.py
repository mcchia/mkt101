"""Top 3 Recommendations + Approval workflow + Execution brief generation."""
from __future__ import annotations

from datetime import date

import streamlit as st

from models import CalendarEntry, CalendarStatus, IdeaStatus
from services.approval import ApprovalError, transition_idea_status
from services.briefs import generate_execution_brief
from services.ideas import select_top3
from services.llm import LLMError
from storage import get_repository
from ui.components import status_badge


def render() -> None:
    st.header("Top 3 Recommendations")
    st.caption(
        "Three is a deliberate ceiling. Each selected idea carries a reason, a primary KPI, "
        "failure modes, and a comparison to the rejected options."
    )

    repo = get_repository()
    brand = repo.get_brand()
    ideas = repo.list_ideas()

    batches = sorted({i.batch_id for i in ideas if i.batch_id})
    if not batches:
        st.info("Generate and score ideas first.")
        return
    default_batch = st.session_state.get("last_idea_batch") or batches[-1]
    selected_batch = st.selectbox(
        "Batch",
        options=batches,
        index=batches.index(default_batch) if default_batch in batches else len(batches) - 1,
    )
    batch_ideas = [i for i in ideas if i.batch_id == selected_batch]
    scored = [i for i in batch_ideas if i.score.total() > 0]
    if not scored:
        st.info("No scored ideas in this batch. Go to **Idea Critique & Scoring** first.")
        return

    cols = st.columns([3, 1])
    cols[0].caption(
        f"{len(scored)} scored ideas in batch · "
        f"{sum(1 for i in batch_ideas if i.selected_top3)} marked top 3"
    )
    if cols[1].button("Pick top 3", type="primary", use_container_width=True):
        with st.spinner("Selecting…"):
            try:
                top3, usage = select_top3(scored, brand)
            except LLMError as e:
                st.error(str(e))
                return
        # persist all of scored (selected_top3 flag, status, reason updated)
        for idea in scored:
            repo.save_idea(idea)
        st.session_state["top3_usage"] = {
            "in": usage.input_tokens,
            "out": usage.output_tokens,
            "cache_read": usage.cache_read,
            "cache_write": usage.cache_write,
        }
        st.success(f"Selected {len(top3)} top ideas.")
        st.rerun()

    top3 = [i for i in batch_ideas if i.selected_top3]
    if not top3:
        return

    for idea in top3:
        with st.container(border=True):
            head = st.columns([3, 1, 1])
            head[0].markdown(f"### {idea.title}")
            head[0].caption(
                f"{idea.platform} · {idea.format or 'format n/a'} · pillar: {idea.pillar or 'n/a'}"
            )
            head[1].markdown(status_badge(idea.status), unsafe_allow_html=True)
            head[2].metric("score", f"{idea.score.total():.2f}")

            if idea.top3_reason:
                with st.expander("Why selected + why it beats rejected options", expanded=True):
                    st.markdown(idea.top3_reason)

            if idea.brief:
                with st.expander("Execution brief", expanded=False):
                    _render_brief(idea.brief)
            else:
                st.info("No execution brief yet.")

            action_cols = st.columns(5)
            if action_cols[0].button("Generate brief", key=f"brief_{idea.id}"):
                with st.spinner("Writing brief…"):
                    try:
                        generate_execution_brief(idea, brand)
                    except LLMError as e:
                        st.error(str(e))
                        return
                repo.save_idea(idea)
                st.rerun()

            if action_cols[1].button("Approve", key=f"approve_{idea.id}"):
                try:
                    transition_idea_status(idea, IdeaStatus.APPROVED, note="Approved from Top 3 view")
                    st.rerun()
                except ApprovalError as e:
                    st.error(str(e))

            if action_cols[2].button("Request changes", key=f"edit_stat_{idea.id}"):
                try:
                    transition_idea_status(idea, IdeaStatus.DRAFT, note="Sent back to draft")
                    st.rerun()
                except ApprovalError as e:
                    st.error(str(e))

            if action_cols[3].button("Reject", key=f"rej_top_{idea.id}"):
                try:
                    transition_idea_status(idea, IdeaStatus.REJECTED, note="Rejected from Top 3 view")
                    st.rerun()
                except ApprovalError as e:
                    st.error(str(e))

            with action_cols[4]:
                st.caption("Schedule")
                target = st.date_input(
                    "Date",
                    value=date.today(),
                    key=f"cal_{idea.id}",
                    label_visibility="collapsed",
                )
                if st.button("Add to calendar", key=f"cal_btn_{idea.id}"):
                    entry = CalendarEntry(
                        idea_id=idea.id,
                        scheduled_for=target,
                        platform=idea.platform,
                        title=idea.title,
                        pillar=idea.pillar,
                        status=CalendarStatus.APPROVED
                        if idea.status == IdeaStatus.APPROVED
                        else CalendarStatus.PLANNED,
                    )
                    repo.save_calendar_entry(entry)
                    if idea.status == IdeaStatus.APPROVED:
                        try:
                            transition_idea_status(idea, IdeaStatus.SCHEDULED, note=f"Scheduled for {target}")
                        except ApprovalError as e:
                            st.warning(str(e))
                    st.success(f"Added to calendar on {target}.")
                    st.rerun()


def _render_brief(brief) -> None:
    st.markdown(f"**Hook** — {brief.hook or '—'}")
    st.markdown(f"**Angle** — {brief.angle or '—'}")
    st.markdown("**Draft caption**")
    st.write(brief.draft_caption or "—")
    st.markdown(f"**Creative direction** — {brief.creative_direction or '—'}")
    if brief.asset_requirements:
        st.markdown("**Asset requirements**")
        for a in brief.asset_requirements:
            st.markdown(f"- {a}")
    st.markdown(f"**CTA** — {brief.cta or '—'}")
    st.markdown(f"**Platform fit** — {', '.join(brief.platform_fit) or '—'}")
    if brief.kpis_to_monitor:
        st.markdown("**KPIs to monitor**")
        for k in brief.kpis_to_monitor:
            st.markdown(f"- {k}")
    if brief.failure_modes:
        st.markdown("**Failure modes**")
        for f in brief.failure_modes:
            st.markdown(f"- {f}")
