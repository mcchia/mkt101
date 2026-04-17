"""Brand Protection page."""

from __future__ import annotations

import streamlit as st

from services import brand_protection


def render() -> None:
    st.title("Brand Protection")
    st.caption(
        "Flags cheap, hypey, or off-brand language before publishing. "
        "Rule-based checks run offline; an optional LLM pass adds nuance."
    )

    text = st.text_area(
        "Text to check (hook, caption, CTA, full idea…)",
        height=200,
        placeholder="Paste the draft you want reviewed.",
    )
    use_llm = st.checkbox("Include LLM nuance review", value=True)
    label = st.text_input("Optional label (for the flag log)")

    col_run, col_log = st.columns([1, 1])
    with col_run:
        run = st.button("Run check", type="primary", use_container_width=True)
    with col_log:
        save_to_log = st.button("Run and log", use_container_width=True)

    if run or save_to_log:
        if not text.strip():
            st.warning("Paste something first.")
            return
        with st.spinner("Checking..."):
            try:
                report = brand_protection.check(text, use_llm=use_llm)
            except Exception as e:
                st.error(f"Check failed: {e}")
                return
        _render_report(report)
        if save_to_log:
            brand_protection.log_report(label or "draft", text, report)
            st.caption("Logged.")

    st.divider()
    st.subheader("Recent logged checks")
    log = brand_protection.list_logged()
    if not log:
        st.info("No logged checks yet.")
        return
    for entry in reversed(log[-20:]):
        rep = entry.get("report", {})
        with st.expander(f"{entry.get('label', '—')} · score {rep.get('score', 0)}"):
            st.code(entry.get("text_snippet", ""), language=None)
            _render_report_from_dict(rep)


def _render_report(report) -> None:
    score = report.score
    bar_color = "green" if score < 20 else ("orange" if score < 50 else "red")
    st.markdown(f"**Score:** :{bar_color}[{score}/100]")
    st.caption(report.summary)
    if not report.flags:
        st.success("No flags.")
        return
    for flag in report.flags:
        with st.container():
            st.markdown(
                f"**{flag.severity.upper()} · {flag.category}** "
                f"(via {flag.source})"
            )
            if flag.excerpt:
                st.markdown(f"> {flag.excerpt[:240]}")
            st.caption(flag.reason)
            st.divider()


def _render_report_from_dict(rep: dict) -> None:
    score = int(rep.get("score", 0))
    bar_color = "green" if score < 20 else ("orange" if score < 50 else "red")
    st.markdown(f"**Score:** :{bar_color}[{score}/100]")
    st.caption(rep.get("summary", ""))
    for flag in rep.get("flags", []):
        st.markdown(
            f"**{str(flag.get('severity', '')).upper()} · {flag.get('category', '')}** "
            f"(via {flag.get('source', '')})"
        )
        if flag.get("excerpt"):
            st.markdown(f"> {flag['excerpt'][:240]}")
        st.caption(flag.get("reason", ""))
        st.divider()
