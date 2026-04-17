"""Sync scheduler page."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from services import scheduler


def render() -> None:
    st.title("Sync Scheduler")
    st.caption(
        "Configure a daily sync. Streamlit cannot reliably host background "
        "daemons, so the app surfaces a 'Run now' button when a run is due and "
        "also supports a standalone runner (`python -m scripts.run_sync`) you "
        "can cron for true automation."
    )

    cfg = scheduler.load_config()

    with st.form("sched_form"):
        enabled = st.checkbox("Enable daily sync", value=cfg.enabled)
        time_of_day = st.text_input("Time of day (HH:MM, 24h local)", value=cfg.time_of_day)
        sources = st.multiselect(
            "Sources to sync",
            options=scheduler.SOURCE_CHOICES,
            default=cfg.normalized_sources(),
        )
        if st.form_submit_button("Save schedule", type="primary"):
            try:
                scheduler.save_config(
                    scheduler.ScheduleConfig(
                        enabled=enabled,
                        time_of_day=time_of_day,
                        sources=sources,
                    )
                )
                st.success("Saved.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))

    st.divider()
    st.subheader("Status")
    cfg = scheduler.load_config()
    next_at = scheduler.next_run_at(cfg)
    last_ok = scheduler.last_successful_run_time()
    due = scheduler.is_due(cfg)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Enabled", "yes" if cfg.enabled else "no")
    with col_b:
        st.metric("Next run", next_at.strftime("%Y-%m-%d %H:%M") if next_at else "—")
    with col_c:
        st.metric("Last successful", last_ok.strftime("%Y-%m-%d %H:%M") if last_ok else "—")

    if due:
        st.warning("A run is due. Click 'Run now' to execute in this process, or let cron run `scripts/run_sync.py`.")

    if st.button("Run now", type="primary"):
        with st.spinner("Running..."):
            entry = scheduler.run_sync_now()
        if entry["status"] == "ok":
            st.success("Sync completed.")
        elif entry["status"] == "noop":
            st.info("Nothing to do (no sources selected).")
        else:
            st.error("Sync finished with errors. See history below.")
        st.rerun()

    st.divider()
    st.subheader("Run history (last 20)")
    history = scheduler.load_history()
    if not history:
        st.info("No runs yet.")
        return
    rows = []
    for entry in reversed(history):
        started = entry.get("started_at")
        rows.append(
            {
                "started": datetime.fromtimestamp(started).strftime("%Y-%m-%d %H:%M:%S") if started else "—",
                "status": entry.get("status", "?"),
                "sources": ", ".join(entry.get("sources", [])),
                "per_source": "; ".join(
                    f"{s['source']}={s['status']}({s.get('summary', '')[:60]})"
                    for s in entry.get("per_source", [])
                ),
            }
        )
    st.dataframe(rows, use_container_width=True)
