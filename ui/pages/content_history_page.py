"""Content History page."""

from __future__ import annotations

import csv
import io

import streamlit as st

from services import content_history


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
    st.title("Content History")
    st.caption(
        "Track hook / angle / format / CTA / pillar across posts so the "
        "assistant can spot repetition and fatigue."
    )

    tab_add, tab_browse, tab_fatigue, tab_import = st.tabs(
        ["Add post", "Browse", "Fatigue signals", "Bulk import"]
    )

    with tab_add:
        with st.form("add_post"):
            col1, col2 = st.columns(2)
            with col1:
                posted_at = st.text_input("Posted at", placeholder="2026-04-10 or 'last Tue'")
                platform = st.selectbox("Platform", ["instagram", "facebook", "both", "other"])
                fmt = st.selectbox("Format", ["reel", "carousel", "static", "story", "live", "ugc", "other"])
                pillar = st.text_input("Content pillar", placeholder="origin stories")
            with col2:
                hook = st.text_area("Hook", height=80)
                angle = st.text_input("Angle", placeholder="craft-led, education-first...")
                cta = st.text_input("CTA", placeholder="Save for later / Shop / Learn more")
            metrics_raw = st.text_area(
                "Metrics (one per line, e.g. `reach=18200`)",
                height=90,
                help="Keys we know: reach, likes, saves, comments, clicks, orders.",
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
        st.caption(f"{len(recs)} records on file.")
        if not recs:
            st.info("No records yet. Add posts in the first tab or bulk import.")
        else:
            for r in reversed(recs[-50:]):
                with st.expander(f"{r.posted_at or '?'} · {r.platform or '?'} · {r.format or '?'} · {r.hook[:60]}"):
                    st.markdown(f"**Hook:** {r.hook}")
                    if r.angle:
                        st.markdown(f"**Angle:** {r.angle}")
                    if r.pillar:
                        st.markdown(f"**Pillar:** {r.pillar}")
                    if r.cta:
                        st.markdown(f"**CTA:** {r.cta}")
                    if r.metrics:
                        st.markdown("**Metrics:** " + ", ".join(f"{k}={int(v) if v.is_integer() else v}" for k, v in r.metrics.items()))
                    if r.notes:
                        st.markdown(f"**Notes:** {r.notes}")
                    if st.button("Delete", key=f"del-{r.id}"):
                        content_history.delete_record(r.id)
                        st.rerun()

    with tab_fatigue:
        lookback = st.slider("Lookback (most recent N posts)", 5, 100, 20)
        rep = content_history.analyze_fatigue(lookback=lookback)
        if rep.warnings:
            st.warning("\n\n".join(f"- {w}" for w in rep.warnings))
        else:
            st.info("No strong fatigue signals in the lookback window.")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("Pillars")
            for p, c in rep.pillar_counts.most_common():
                st.text(f"{c}  {p}")
        with col2:
            st.subheader("Formats")
            for p, c in rep.format_counts.most_common():
                st.text(f"{c}  {p}")
        with col3:
            st.subheader("CTAs")
            for p, c in rep.cta_counts.most_common():
                st.text(f"{c}  {p}")

        st.subheader("Repeated hooks")
        if not rep.hook_clusters:
            st.caption("No hooks recorded.")
        else:
            for hook, c in rep.hook_clusters[:10]:
                st.text(f"{c}x  {hook[:100]}")

    with tab_import:
        st.markdown(
            "Paste CSV with columns: "
            "`posted_at,platform,hook,angle,format,cta,pillar,reach,likes,saves,comments,clicks,orders,notes` "
            "(metric columns optional)."
        )
        raw = st.text_area("CSV", height=180)
        if st.button("Import"):
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
