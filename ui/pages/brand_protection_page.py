"""Brand Protection page."""

from __future__ import annotations

import streamlit as st

from services import brand_protection
from ui import styling


_SEVERITY_TONE = {"low": "info", "medium": "warning", "high": "danger"}


def render() -> None:
    styling.page_header(
        "Brand Protection",
        subtitle=(
            "Flags cheap, hypey, or off-brand language before publishing. "
            "Rule-based checks run offline. An optional LLM pass adds nuance."
        ),
        eyebrow="Protection & ops",
    )

    with styling.card():
        text = st.text_area(
            "Text to check (hook, caption, CTA, full idea…)",
            height=200,
            placeholder="Paste the draft you want reviewed.",
        )
        col_a, col_b, col_c = st.columns([2, 2, 3])
        with col_a:
            use_llm = st.toggle("Include LLM nuance review", value=True)
        with col_b:
            label = st.text_input("Optional label", placeholder="e.g. Oct launch caption v2")
        with col_c:
            st.write("")
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                run = st.button("Run check", type="primary", use_container_width=True)
            with col_r2:
                save_to_log = st.button("Run and log", use_container_width=True)

    if run or save_to_log:
        if not text.strip():
            st.warning("Paste something first.")
        else:
            with st.spinner("Checking..."):
                try:
                    report = brand_protection.check(text, use_llm=use_llm)
                    _render_report(report)
                    if save_to_log:
                        brand_protection.log_report(label or "draft", text, report)
                        st.caption("Logged.")
                except Exception as e:
                    st.error(f"Check failed: {e}")

    styling.section("Recent logged checks")
    log = brand_protection.list_logged()
    if not log:
        styling.empty_state(
            "No logged checks yet",
            "Use 'Run and log' above to save a check for later review.",
        )
        return
    for entry in reversed(log[-20:]):
        rep = entry.get("report", {})
        score = int(rep.get("score", 0))
        tone = styling.tone_for_score(score)
        title = f"{entry.get('label', '—')}  ·  score {score}"
        with st.expander(title):
            st.markdown(
                f"{styling.badge_html(f'score {score}', tone)}&nbsp;&nbsp;"
                f"<span style='color:var(--tea-muted);font-size:0.88rem;'>"
                f"{rep.get('summary', '')}</span>",
                unsafe_allow_html=True,
            )
            styling.quote(entry.get("text_snippet", ""))
            _render_flags(rep.get("flags", []))


def _render_report(report) -> None:
    score = report.score
    tone = styling.tone_for_score(score)
    with styling.card():
        col_score, col_summary = st.columns([1, 3])
        with col_score:
            st.markdown(
                f"<div style='font-size:0.78rem;color:var(--tea-muted);"
                f"text-transform:uppercase;letter-spacing:0.08em;'>Risk score</div>"
                f"<div style='font-family:var(--tea-serif);font-size:2.2rem;"
                f"color:var(--tea-ink);font-weight:600;line-height:1;'>{score}<span style='color:var(--tea-muted);font-size:1rem;'> / 100</span></div>"
                f"<div style='margin-top:0.35rem;'>{styling.badge_html(_level(score), tone)}</div>",
                unsafe_allow_html=True,
            )
        with col_summary:
            st.markdown(
                f"<div style='font-size:0.88rem;color:var(--tea-ink-soft);'>"
                f"{report.summary}</div>",
                unsafe_allow_html=True,
            )

    if not report.flags:
        st.success("No premium-brand risks detected.")
        return

    styling.section(f"Flags ({len(report.flags)})")
    _render_flags([_flag_dict(f) for f in report.flags])


def _render_flags(flags: list[dict]) -> None:
    for flag in flags:
        severity = str(flag.get("severity", "low"))
        tone = _SEVERITY_TONE.get(severity, "neutral")
        category = flag.get("category", "")
        source = flag.get("source", "")
        with styling.card():
            st.markdown(
                f"{styling.badge_html(severity.upper(), tone)} "
                f"{styling.badge_html(category, 'neutral')} "
                f"<span style='color:var(--tea-muted);font-size:0.8rem;margin-left:0.5rem;'>via {source}</span>",
                unsafe_allow_html=True,
            )
            excerpt = flag.get("excerpt", "")
            if excerpt:
                styling.quote(excerpt[:240])
            reason = flag.get("reason", "")
            if reason:
                st.markdown(
                    f"<div style='color:var(--tea-ink-soft);font-size:0.9rem;'>"
                    f"{reason}</div>",
                    unsafe_allow_html=True,
                )


def _flag_dict(flag) -> dict:
    return {
        "category": flag.category,
        "severity": flag.severity,
        "excerpt": flag.excerpt,
        "reason": flag.reason,
        "source": flag.source,
    }


def _level(score: int) -> str:
    if score < 20:
        return "low risk"
    if score < 50:
        return "medium risk"
    return "high risk"
