"""Content Calendar — weekly view + status transitions."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from models import CalendarEntry, CalendarStatus, IdeaStatus
from services.approval import ApprovalError, transition_idea_status
from storage import get_repository


def render() -> None:
    st.header("Content Calendar")
    st.caption("Weekly plan. Pulls from approved / scheduled ideas; you can also add ad-hoc entries.")

    repo = get_repository()
    entries = repo.list_calendar()

    cols = st.columns([1, 1, 2])
    start = cols[0].date_input("Week starting", value=_monday_of(date.today()))
    weeks = cols[1].number_input("Weeks", 1, 8, value=2)

    start_d = _monday_of(start)
    end_d = start_d + timedelta(days=7 * int(weeks) - 1)

    in_range = [e for e in entries if start_d <= e.scheduled_for <= end_d]
    in_range.sort(key=lambda e: (e.scheduled_for, e.platform))

    st.markdown(f"### {start_d.isoformat()} → {end_d.isoformat()}")

    if not in_range:
        st.info("No entries in this range.")
    else:
        df = pd.DataFrame(
            [
                {
                    "date": e.scheduled_for.isoformat(),
                    "platform": e.platform,
                    "pillar": e.pillar or "",
                    "title": e.title,
                    "status": e.status.value,
                    "id": e.id,
                }
                for e in in_range
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)

        with st.expander("Per-entry actions", expanded=False):
            for e in in_range:
                row_cols = st.columns([2, 1, 1, 1, 1])
                row_cols[0].write(f"**{e.scheduled_for}** · {e.platform} · {e.title}")
                if row_cols[1].button("Approved", key=f"cal_ap_{e.id}"):
                    e.status = CalendarStatus.APPROVED
                    repo.save_calendar_entry(e)
                    _bump_idea(e, IdeaStatus.APPROVED)
                    st.rerun()
                if row_cols[2].button("Scheduled", key=f"cal_sc_{e.id}"):
                    e.status = CalendarStatus.SCHEDULED
                    repo.save_calendar_entry(e)
                    _bump_idea(e, IdeaStatus.SCHEDULED)
                    st.rerun()
                if row_cols[3].button("Posted", key=f"cal_po_{e.id}"):
                    e.status = CalendarStatus.POSTED
                    repo.save_calendar_entry(e)
                    _bump_idea(e, IdeaStatus.POSTED)
                    st.rerun()
                if row_cols[4].button("Remove", key=f"cal_rm_{e.id}"):
                    repo.delete_calendar_entry(e.id)
                    st.rerun()

    st.divider()
    st.markdown("#### Add ad-hoc entry")
    with st.form("new_cal", clear_on_submit=True):
        cols = st.columns(3)
        title = cols[0].text_input("Title")
        platform = cols[1].selectbox("Platform", ["instagram", "facebook", "both"])
        scheduled = cols[2].date_input("Date", value=date.today())
        cols2 = st.columns(2)
        pillar = cols2[0].text_input("Pillar")
        notes = cols2[1].text_input("Notes")
        submitted = st.form_submit_button("Add entry", use_container_width=True)
    if submitted and title:
        entry = CalendarEntry(
            title=title,
            platform=platform,
            scheduled_for=scheduled,
            pillar=pillar,
            notes=notes,
            status=CalendarStatus.PLANNED,
        )
        repo.save_calendar_entry(entry)
        st.success("Added.")
        st.rerun()


def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _bump_idea(entry: CalendarEntry, new_status: IdeaStatus) -> None:
    if not entry.idea_id:
        return
    repo = get_repository()
    idea = repo.get_idea(entry.idea_id)
    if not idea:
        return
    try:
        transition_idea_status(idea, new_status, note=f"Calendar sync: {entry.id}")
    except ApprovalError:
        # skip silently; approval rules take precedence
        pass
