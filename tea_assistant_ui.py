"""Streamlit UI for the tea brand AI marketing assistant.

Usage:
    # Set ANTHROPIC_API_KEY via your environment, a local .env file, or
    # .streamlit/secrets.toml. Never hardcode or commit the key.
    streamlit run tea_assistant_ui.py
"""

import anthropic
import streamlit as st

from config import get_api_key, redact
from tea_assistant import MODEL, SYSTEM_PROMPT

st.set_page_config(page_title="Tea Marketing Assistant", layout="wide")
st.title("AI Marketing Assistant — tea brand")
st.caption("Paste recent post metrics and a goal. The assistant will clarify, analyze, and produce execution-ready output.")

try:
    api_key = get_api_key()
except RuntimeError as e:
    # Error message from config.get_api_key() never contains the key.
    st.error(str(e))
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "usage" not in st.session_state:
    st.session_state.usage = None

with st.sidebar:
    st.subheader("Session")
    if st.button("Reset conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.usage = None
        st.rerun()
    st.caption(f"Turns: {len(st.session_state.messages) // 2}")
    if st.session_state.usage:
        u = st.session_state.usage
        st.divider()
        st.subheader("Last turn tokens")
        st.text(
            f"in:          {u['in']}\n"
            f"out:         {u['out']}\n"
            f"cache_read:  {u['cache_read']}\n"
            f"cache_write: {u['cache_write']}"
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

    def stream_text():
        with client.messages.stream(
            model=MODEL,
            max_tokens=64000,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
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
