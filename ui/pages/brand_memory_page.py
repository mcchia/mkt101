"""Brand Memory page."""

from __future__ import annotations

import streamlit as st

from services import brand_memory


def _text_area(label: str, value: str, *, height: int = 90, help: str | None = None) -> str:
    return st.text_area(label, value=value, height=height, help=help)


def _list_area(label: str, values: list[str], *, height: int = 120, help: str | None = None) -> list[str]:
    raw = st.text_area(label, value="\n".join(values), height=height, help=help)
    return [line.strip() for line in raw.splitlines() if line.strip()]


def render() -> None:
    st.title("Brand Memory")
    st.caption(
        "Editable brand memory is authoritative. It feeds analysis, idea "
        "generation, critique, top-3 selection, and execution briefs."
    )

    editable = brand_memory.load_editable()
    inferred = brand_memory.load_inferred()

    tab_edit, tab_inferred = st.tabs(["Editable (truth)", "Inferred (suggestions)"])

    with tab_edit:
        with st.form("brand_memory_form"):
            tone = _text_area("Tone of voice", editable.tone_of_voice)
            audience = _text_area("Target audience", editable.target_audience)
            pillars = _list_area(
                "Content pillars (one per line)",
                editable.content_pillars,
                help="E.g. origin stories, brewing rituals, pairings, education.",
            )
            guardrails = _list_area(
                "Premium guardrails (one per line)",
                editable.premium_guardrails,
                help="Things the brand always protects or never does.",
            )
            banned = _list_area(
                "Banned phrases (one per line)",
                editable.banned_phrases,
                help="Exact phrases the assistant must never use. Case-insensitive.",
            )
            cta_style = _text_area("Preferred CTA style", editable.preferred_cta_style)
            positioning = _text_area(
                "Positioning notes",
                editable.positioning_notes,
                height=120,
            )
            constraints = _text_area(
                "Posting constraints",
                editable.posting_constraints,
                help="Frequency, platforms, formats, approval workflow, etc.",
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
            "Inferred notes are model suggestions. They do NOT override the "
            "editable truth above. Promote any line manually if you want it "
            "to be authoritative."
        )
        if inferred.is_empty():
            st.info("No inferred notes yet. Use the Assistant to build up observations.")
        else:
            if inferred.tone_of_voice:
                st.markdown(f"**Tone:** {inferred.tone_of_voice}")
            if inferred.target_audience:
                st.markdown(f"**Audience:** {inferred.target_audience}")
            if inferred.content_pillars:
                st.markdown("**Pillars:** " + ", ".join(inferred.content_pillars))
            if inferred.premium_guardrails:
                st.markdown("**Guardrails:**")
                for g in inferred.premium_guardrails:
                    st.markdown(f"- {g}")
            if inferred.banned_phrases:
                st.markdown("**Banned phrases (suggested):**")
                for p in inferred.banned_phrases:
                    st.markdown(f"- {p}")
            if inferred.preferred_cta_style:
                st.markdown(f"**CTA style:** {inferred.preferred_cta_style}")
            if inferred.positioning_notes:
                st.markdown(f"**Positioning notes:** {inferred.positioning_notes}")
            if inferred.posting_constraints:
                st.markdown(f"**Posting constraints:** {inferred.posting_constraints}")

    st.divider()
    st.subheader("Preview: what the assistant will see")
    preview = brand_memory.system_block()
    if preview:
        st.code(preview, language="markdown")
    else:
        st.info("Brand memory is empty. Add at least tone, audience, and pillars for best results.")
