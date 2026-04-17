"""Sync / Logs / Status page. Shows sync history and decision log."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from storage import get_repository


def render() -> None:
    st.header("Sync / Logs / Status")
    st.caption("Ingestion runs and auditable decision history.")

    repo = get_repository()

    st.markdown("#### Sync runs")
    syncs = sorted(repo.list_syncs(), key=lambda s: s.started_at, reverse=True)
    if syncs:
        df = pd.DataFrame(
            [
                {
                    "id": s.id,
                    "source": s.source.value,
                    "status": s.status.value,
                    "started": s.started_at,
                    "finished": s.finished_at,
                    "ingested": s.records_ingested,
                    "skipped": s.records_skipped,
                    "details": s.details,
                    "errors": "; ".join(s.errors) if s.errors else "",
                }
                for s in syncs
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No syncs yet.")

    st.divider()

    st.markdown("#### Decision log")
    decisions = sorted(repo.list_decisions(), key=lambda d: d.at, reverse=True)
    if decisions:
        df = pd.DataFrame(
            [
                {
                    "at": d.at,
                    "actor": d.actor,
                    "entity": d.entity_type,
                    "id": d.entity_id,
                    "action": d.action,
                    "from": d.from_status,
                    "to": d.to_status,
                    "note": d.note,
                }
                for d in decisions
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No approval actions yet.")

    st.divider()

    st.markdown("#### Crawled / ingested source records")
    sources = repo.list_sources()
    if sources:
        df = pd.DataFrame(
            [
                {
                    "ingested_at": s.ingested_at,
                    "type": s.source_type.value,
                    "url": s.url,
                    "title": s.title,
                    "tags": ", ".join(s.tags),
                }
                for s in sources
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No source records yet.")
