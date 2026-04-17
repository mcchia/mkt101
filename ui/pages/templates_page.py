"""Templates page: one-click reusable workflows."""

from __future__ import annotations

import anthropic
import streamlit as st

from config import redact
from services import llm, templates


def render() -> None:
    st.title("Templates")
    st.caption(
        "Prefilled workflows for recurring tasks. Each template injects brand "
        "memory, content history, and winning/losing patterns automatically."
    )

    tab_run, tab_manage = st.tabs(["Run template", "Manage custom templates"])

    with tab_run:
        all_templates = templates.list_all()
        if not all_templates:
            st.info("No templates available.")
            return
        pick = st.selectbox(
            "Template",
            options=[t.id for t in all_templates],
            format_func=lambda tid: next((f"{t.name} ({'built-in' if t.built_in else 'custom'})" for t in all_templates if t.id == tid), tid),
        )
        tpl = templates.get(pick)
        if not tpl:
            return
        st.caption(tpl.description)
        with st.expander("Template prompt"):
            st.code(tpl.prompt, language="markdown")
        notes = st.text_area("Additional notes / inputs", height=120)
        if st.button("Run template", type="primary"):
            prompt, extra_system = templates.assemble_prompt(tpl, user_notes=notes)
            with st.chat_message("assistant"):
                placeholder = st.empty()
                acc: list[str] = []
                try:
                    for delta in llm.stream_text(prompt, extra_system=extra_system, max_tokens=32000):
                        acc.append(delta)
                        placeholder.markdown("".join(acc))
                except anthropic.APIError as e:
                    st.error(f"API error: {redact(e)}")
                except Exception as e:
                    st.error(f"Unexpected error: {redact(e)}")

    with tab_manage:
        st.subheader("Create a custom template")
        with st.form("tpl_form"):
            name = st.text_input("Name")
            description = st.text_input("Description")
            prompt = st.text_area("Prompt body", height=180)
            sections = st.text_area(
                "Output sections (one per line)",
                height=120,
                placeholder="Performance summary\nDecisions\nPost ideas",
            )
            if st.form_submit_button("Save"):
                try:
                    templates.save_custom(
                        name=name,
                        description=description,
                        prompt=prompt,
                        output_sections=[s.strip() for s in sections.splitlines() if s.strip()],
                    )
                    st.success("Saved.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

        st.subheader("Existing custom templates")
        customs = [t for t in templates.list_all() if not t.built_in]
        if not customs:
            st.info("No custom templates yet.")
        for t in customs:
            with st.expander(t.name):
                st.caption(t.description)
                st.code(t.prompt, language="markdown")
                if st.button("Delete", key=f"del-tpl-{t.id}"):
                    templates.delete_custom(t.id)
                    st.rerun()
