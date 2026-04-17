"""Chat page: original analyze -> ideate -> critique -> top 3 -> execute flow.

Extended to inject brand memory, recent content history, and pattern context
into the system prompt so every step is aware of them.
"""

from __future__ import annotations

import anthropic
import streamlit as st

from config import get_api_key, redact
from services import brand_memory, content_history, losing_posts, patterns
from tea_assistant import MODEL, SYSTEM_PROMPT
from ui import styling


def _build_extra_system() -> str:
    blocks = [
        brand_memory.system_block(),
        content_history.system_block(),
        patterns.system_block(),
        losing_posts.system_block(),
    ]
    return "\n\n".join(b for b in blocks if b)


def _context_summary() -> list[tuple[str, str]]:
    bm = brand_memory.load_editable()
    ch_count = len(content_history.list_records())
    return [
        ("Brand memory", "configured" if not bm.is_empty() else "empty"),
        ("Content history", f"{ch_count} record{'s' if ch_count != 1 else ''}"),
        ("Patterns", "loaded" if patterns.last_saved_summary() else "not yet extracted"),
    ]


def render() -> None:
    styling.page_header(
        "Assistant",
        subtitle=(
            "Paste post metrics and a goal. The assistant clarifies, analyzes, "
            "and produces execution-ready output. Brand memory and content "
            "history feed every turn automatically."
        ),
        eyebrow="Workspace",
    )

    try:
        api_key = get_api_key()
    except RuntimeError as e:
        st.error(str(e))
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "usage" not in st.session_state:
        st.session_state.usage = None

    with st.sidebar:
        styling.section("Session")
        if st.button("Reset conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.usage = None
            st.rerun()
        turns = len(st.session_state.messages) // 2
        st.caption(f"{turns} turn{'s' if turns != 1 else ''}")

        styling.section("Context in use")
        for label, value in _context_summary():
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;"
                f"padding:0.2rem 0;font-size:0.85rem;'>"
                f"<span style='color:var(--tea-muted);'>{label}</span>"
                f"<span style='color:var(--tea-ink);'>{value}</span></div>",
                unsafe_allow_html=True,
            )

        if st.session_state.usage:
            u = st.session_state.usage
            styling.section("Last turn tokens")
            st.markdown(
                f"<div style='font-size:0.82rem;color:var(--tea-muted);line-height:1.7;'>"
                f"input <span style='float:right;color:var(--tea-ink);'>{u['in']}</span><br>"
                f"output <span style='float:right;color:var(--tea-ink);'>{u['out']}</span><br>"
                f"cache read <span style='float:right;color:var(--tea-ink);'>{u['cache_read']}</span><br>"
                f"cache write <span style='float:right;color:var(--tea-ink);'>{u['cache_write']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    if not st.session_state.messages:
        styling.empty_state(
            "Start a conversation",
            "Share recent post metrics, a goal, and any context. Ask for a weekly read, a campaign kickoff, or a product launch plan.",
        )

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Message (Shift+Enter for new line)")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        client = anthropic.Anthropic(api_key=api_key)
        extra = _build_extra_system()
        system_blocks: list[dict] = [
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        if extra:
            system_blocks.append({"type": "text", "text": extra})

        def stream_text():
            with client.messages.stream(
                model=MODEL,
                max_tokens=64000,
                system=system_blocks,
                thinking={"type": "adaptive"},
                output_config={"effort": "high"},
                messages=st.session_state.messages,
            ) as stream:
                for event in stream:
                    if event.type == "content_block_delta" and event.delta.type == "text_delta":
                        yield event.delta.text
                final = stream.get_final_message()
            usage = final.usage
            st.session_state.usage = {
                "in": usage.input_tokens,
                "out": usage.output_tokens,
                "cache_read": getattr(usage, "cache_read_input_tokens", 0) or 0,
                "cache_write": getattr(usage, "cache_creation_input_tokens", 0) or 0,
            }

        try:
            with st.chat_message("assistant"):
                full_text = st.write_stream(stream_text)
            st.session_state.messages.append({"role": "assistant", "content": full_text})
            st.rerun()
        except anthropic.APIError as e:
            st.session_state.messages.pop()
            st.error(f"API error: {redact(e)}")
        except Exception as e:
            st.session_state.messages.pop()
            st.error(f"Unexpected error: {redact(e)}")
