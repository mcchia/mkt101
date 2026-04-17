"""Templates page: one-click reusable workflows."""

from __future__ import annotations

import anthropic
import streamlit as st

from config import redact
from services import llm, templates
from ui import styling


def render() -> None:
    styling.page_header(
        "Templates",
        subtitle=(
            "Prefilled workflows for recurring tasks. Each template injects "
            "brand memory, content history, and winning/losing patterns "
            "automatically."
        ),
        eyebrow="Workspace",
    )

    tab_run, tab_manage = st.tabs(["Run a template", "Manage custom templates"])

    with tab_run:
        all_templates = templates.list_all()
        if not all_templates:
            styling.empty_state("No templates available", "Custom templates you save will appear here.")
            return

        styling.section("Choose a template")
        cols = st.columns(2)
        if "tea_selected_template" not in st.session_state:
            st.session_state.tea_selected_template = all_templates[0].id

        for i, t in enumerate(all_templates):
            with cols[i % 2]:
                with styling.card():
                    tag = "Built-in" if t.built_in else "Custom"
                    tone = "info" if t.built_in else "neutral"
                    st.markdown(
                        f"{styling.badge_html(tag, tone)}&nbsp;&nbsp;"
                        f"<span style='font-family:var(--tea-serif);font-size:1.05rem;"
                        f"font-weight:600;color:var(--tea-ink);'>{t.name}</span>",
                        unsafe_allow_html=True,
                    )
                    st.caption(t.description)
                    selected = st.session_state.tea_selected_template == t.id
                    btn_label = "Selected" if selected else "Use this template"
                    if st.button(btn_label, key=f"pick-{t.id}", use_container_width=True, disabled=selected):
                        st.session_state.tea_selected_template = t.id
                        st.rerun()

        tpl = templates.get(st.session_state.tea_selected_template)
        if not tpl:
            return

        styling.section(f"Run: {tpl.name}")
        with st.expander("Template prompt"):
            st.code(tpl.prompt, language="markdown")
        notes = st.text_area("Additional notes or inputs", height=120)
        run = st.button("Run template", type="primary")

        if run:
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
        styling.section("Create a custom template")
        with st.form("tpl_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                name = st.text_input("Name")
            with col_b:
                description = st.text_input("Description")
            prompt = st.text_area("Prompt body", height=180)
            sections = st.text_area(
                "Output sections (one per line)",
                height=120,
                placeholder="Performance summary\nDecisions\nPost ideas",
            )
            if st.form_submit_button("Save custom template", type="primary"):
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

        styling.section("Existing custom templates")
        customs = [t for t in templates.list_all() if not t.built_in]
        if not customs:
            styling.empty_state("No custom templates", "Save one above.")
        for t in customs:
            with st.expander(t.name):
                st.caption(t.description)
                st.code(t.prompt, language="markdown")
                if st.button("Delete", key=f"del-tpl-{t.id}"):
                    templates.delete_custom(t.id)
                    st.rerun()
