"""Content History page."""

from __future__ import annotations

import csv
import io

import streamlit as st

from services import content_history
from ui import styling


def _parse_metrics(raw: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for part in raw.replace(",", "\n").splitlines():
        if "=" not in part and ":" not in part:
            continue
        sep = "=" if "=" in part else ":"
        k, v = part.split(sep, 1)
        try:
            out[k.strip().lower()] = float(v.strip())
        except ValueError:
            continue
    return out


def render() -> None:
    styling.page_header(
        "Content History",
        subtitle=(
            "Track hook, angle, format, CTA, and pillar across posts so the "
            "assistant can spot repetition and fatigue."
        ),
        eyebrow="Knowledge",
    )

    tab_add, tab_browse, tab_fatigue, tab_import = st.tabs(
        ["Add post", "Browse", "Fatigue signals", "Bulk import"]
    )

    with tab_add:
        with st.form("add_post"):
            col1, col2 = st.columns(2)
            with col1:
                posted_at = st.text_input("Posted at", placeholder="2026-04-10")
                platform = st.selectbox("Platform", ["instagram", "facebook", "both", "other"])
                fmt = st.selectbox("Format", ["reel", "carousel", "static", "story", "live", "ugc", "other"])
                pillar = st.text_input("Content pillar", placeholder="origin stories")
            with col2:
                hook = st.text_area("Hook", height=80)
                angle = st.text_input("Angle", placeholder="craft-led, education-first")
                cta = st.text_input("CTA", placeholder="Save for later · Shop · Learn more")
            metrics_raw = st.text_area(
                "Metrics (one per line, e.g. `reach=18200`)",
                height=90,
                help="Known keys: reach, likes, saves, comments, clicks, orders.",
            )
            notes = st.text_area("Caption / notes", height=80)
            if st.form_submit_button("Add record", type="primary"):
                if not hook.strip():
                    st.error("Hook is required.")
                else:
                    content_history.add_record(
                        posted_at=posted_at,
                        platform=platform,
                        hook=hook,
                        angle=angle,
                        format=fmt,
                        cta=cta,
                        pillar=pillar,
                        metrics=_parse_metrics(metrics_raw),
                        notes=notes,
                    )
                    st.success("Record added.")
                    st.rerun()

    with tab_browse:
        recs = content_history.list_records()
        c1, _ = st.columns([1, 3])
        with c1:
            st.metric("Records", len(recs))
        if not recs:
            styling.empty_state(
                "No records yet",
                "Add posts in the first tab or bulk import a CSV.",
            )
        else:
            for r in reversed(recs[-50:]):
                title = f"{r.posted_at or '—'} · {r.platform or '—'} · {r.format or '—'} · {r.hook[:70]}"
                with st.expander(title):
                    styling.kv_list(
                        [
                            ("Hook", r.hook),
                            ("Angle", r.angle),
                            ("Pillar", r.pillar),
                            ("CTA", r.cta),
                        ]
                    )
                    if r.metrics:
                        st.markdown(
                            "**Metrics:** "
                            + ", ".join(
                                f"{k}={int(v) if v.is_integer() else v}"
                                for k, v in r.metrics.items()
                            )
                        )
                    if r.notes:
                        styling.quote(r.notes)
                    if st.button("Delete", key=f"del-{r.id}"):
                        content_history.delete_record(r.id)
                        st.rerun()

    with tab_fatigue:
        lookback = st.slider("Lookback (most recent N posts)", 5, 100, 20)
        rep = content_history.analyze_fatigue(lookback=lookback)

        if rep.warnings:
            for w in rep.warnings:
                st.warning(w)
        else:
            st.info("No strong fatigue signals in the lookback window.")

        styling.section("Distribution")
        col1, col2, col3 = st.columns(3)
        for col, label, counts in [
            (col1, "Pillars", rep.pillar_counts),
            (col2, "Formats", rep.format_counts),
            (col3, "CTAs", rep.cta_counts),
        ]:
            with col:
                with styling.card():
                    st.markdown(f"**{label}**")
                    if not counts:
                        st.caption("—")
                    for name, c in counts.most_common():
                        st.markdown(
                            f"<div style='display:flex;justify-content:space-between;"
                            f"padding:0.15rem 0;font-size:0.88rem;'>"
                            f"<span>{name}</span><span style='color:var(--tea-muted);'>{c}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

        styling.section("Repeated hooks")
        if not rep.hook_clusters:
            st.caption("No hooks recorded.")
        else:
            for hook, c in rep.hook_clusters[:10]:
                tone = "danger" if c >= 3 else ("warning" if c == 2 else "neutral")
                st.markdown(
                    f"{styling.badge_html(f'{c}x', tone)} &nbsp; {hook[:120]}",
                    unsafe_allow_html=True,
                )

    with tab_import:
        st.caption(
            "Paste CSV with columns: "
            "`posted_at, platform, hook, angle, format, cta, pillar, reach, likes, saves, comments, clicks, orders, notes`. "
            "Metric columns are optional."
        )
        raw = st.text_area("CSV", height=180, label_visibility="collapsed")
        if st.button("Import", type="primary"):
            if not raw.strip():
                st.warning("Paste some CSV first.")
            else:
                try:
                    reader = csv.DictReader(io.StringIO(raw))
                    rows: list[dict] = []
                    for row in reader:
                        metrics = {}
                        for k in ("reach", "likes", "saves", "comments", "clicks", "orders"):
                            v = row.get(k)
                            if v not in (None, "", "NA"):
                                metrics[k] = v
                        rows.append(
                            {
                                "posted_at": row.get("posted_at", ""),
                                "platform": row.get("platform", ""),
                                "hook": row.get("hook", ""),
                                "angle": row.get("angle", ""),
                                "format": row.get("format", ""),
                                "cta": row.get("cta", ""),
                                "pillar": row.get("pillar", ""),
                                "metrics": metrics,
                                "notes": row.get("notes", ""),
                            }
                        )
                    added = content_history.import_records(rows)
                    st.success(f"Imported {added} records.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not parse CSV: {e}")
