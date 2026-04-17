"""Brand Memory page."""

from __future__ import annotations

import streamlit as st

from services import brand_memory
from ui import styling


def _text_area(label: str, value: str, *, height: int = 90, help: str | None = None) -> str:
    return st.text_area(label, value=value, height=height, help=help)


def _list_area(label: str, values: list[str], *, height: int = 120, help: str | None = None) -> list[str]:
    raw = st.text_area(label, value="\n".join(values), height=height, help=help)
    return [line.strip() for line in raw.splitlines() if line.strip()]


def render() -> None:
    styling.page_header(
        "Brand Memory",
        subtitle=(
            "Editable brand memory is authoritative. It feeds analysis, idea "
            "generation, critique, top-3 selection, and execution briefs."
        ),
        eyebrow="Knowledge",
    )

    editable = brand_memory.load_editable()
    inferred = brand_memory.load_inferred()

    tab_edit, tab_inferred, tab_preview = st.tabs(
        ["Editable truth", "Inferred suggestions", "System preview"]
    )

    with tab_edit:
        with st.form("brand_memory_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                tone = _text_area("Tone of voice", editable.tone_of_voice)
                audience = _text_area("Target audience", editable.target_audience)
                cta_style = _text_area("Preferred CTA style", editable.preferred_cta_style)
            with col_b:
                positioning = _text_area("Positioning notes", editable.positioning_notes, height=120)
                constraints = _text_area(
                    "Posting constraints",
                    editable.posting_constraints,
                    help="Frequency, platforms, formats, approval workflow.",
                )

            styling.section("Pillars and guardrails")
            col_c, col_d, col_e = st.columns(3)
            with col_c:
                pillars = _list_area(
                    "Content pillars",
                    editable.content_pillars,
                    help="One per line. E.g. origin stories, brewing rituals.",
                )
            with col_d:
                guardrails = _list_area(
                    "Premium guardrails",
                    editable.premium_guardrails,
                    help="Things the brand always protects or never does.",
                )
            with col_e:
                banned = _list_area(
                    "Banned phrases",
                    editable.banned_phrases,
                    help="Case-insensitive. Used by brand protection.",
                )

            submitted = st.form_submit_button("Save brand memory", type="primary")
            if submitted:
                mem = brand_memory.BrandMemory(
                    tone_of_voice=tone,
                    target_audience=audience,
                    content_pillars=pillars,
                    premium_guardrails=guardrails,
                    banned_phrases=banned,
                    preferred_cta_style=cta_style,
                    positioning_notes=positioning,
                    posting_constraints=constraints,
                )
                try:
                    brand_memory.save_editable(mem)
                    st.success("Saved. New turns will use this memory.")
                except Exception as e:
                    st.error(f"Could not save: {e}")

    with tab_inferred:
        st.caption(
            "Inferred notes are model suggestions. They do not override the "
            "editable truth. Promote any line manually."
        )
        if inferred.is_empty():
            styling.empty_state(
                "No inferred notes yet",
                "Run analyses on the Assistant page. Over time you can promote observations here into the editable truth.",
            )
        else:
            with styling.card():
                styling.kv_list(
                    [
                        ("Tone", inferred.tone_of_voice),
                        ("Audience", inferred.target_audience),
                        ("CTA style", inferred.preferred_cta_style),
                        ("Positioning", inferred.positioning_notes),
                        ("Constraints", inferred.posting_constraints),
                    ]
                )
                if inferred.content_pillars:
                    st.markdown("**Pillars**")
                    for g in inferred.content_pillars:
                        st.markdown(f"- {g}")
                if inferred.premium_guardrails:
                    st.markdown("**Guardrails**")
                    for g in inferred.premium_guardrails:
                        st.markdown(f"- {g}")
                if inferred.banned_phrases:
                    st.markdown("**Banned phrases (suggested)**")
                    for p in inferred.banned_phrases:
                        st.markdown(f"- {p}")

    with tab_preview:
        styling.section("What the assistant will see", "Injected as an additional system block alongside the marketing spec.")
        preview = brand_memory.system_block()
        if preview:
            st.code(preview, language="markdown")
        else:
            styling.empty_state(
                "Brand memory is empty",
                "Add at least tone, audience, and pillars for best results.",
            )
