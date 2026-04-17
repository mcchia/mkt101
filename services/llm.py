"""Shared Claude client helpers used by all new services.

Keeps the existing secure config pattern: `get_api_key()` + `redact()`.
Never logs or persists the API key. Callers pass a concrete user prompt
and an optional extra system block (for brand memory or feature-specific
directives). The main marketing system prompt stays cached.
"""

from __future__ import annotations

import json
from typing import Iterable, Optional

import anthropic

from config import get_api_key, redact
from tea_assistant import MODEL, SYSTEM_PROMPT


def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=get_api_key())


def build_system_blocks(extra: Optional[str] = None) -> list[dict]:
    """Return cached system blocks, optionally followed by a feature-specific block."""
    blocks: list[dict] = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    if extra and extra.strip():
        blocks.append({"type": "text", "text": extra.strip()})
    return blocks


def run_text(
    user_prompt: str,
    *,
    extra_system: Optional[str] = None,
    max_tokens: int = 8000,
    effort: str = "high",
) -> str:
    """Single-turn text completion, non-streaming. Returns the full text."""
    client = get_client()
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=build_system_blocks(extra_system),
            thinking={"type": "adaptive"},
            output_config={"effort": effort},
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.APIError as e:
        raise RuntimeError(f"Claude API error: {redact(e)}") from None

    parts: list[str] = []
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip()


def run_json(
    user_prompt: str,
    *,
    extra_system: Optional[str] = None,
    max_tokens: int = 8000,
) -> dict | list:
    """Ask for a single JSON object/array and parse it.

    The prompt must instruct the model to emit JSON only. We are defensive:
    we strip code fences and pull the first {...} or [...] block.
    """
    text = run_text(user_prompt, extra_system=extra_system, max_tokens=max_tokens)
    return _extract_json(text)


def stream_text(
    user_prompt: str,
    *,
    extra_system: Optional[str] = None,
    max_tokens: int = 8000,
) -> Iterable[str]:
    """Yield text deltas for UI streaming."""
    client = get_client()
    with client.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        system=build_system_blocks(extra_system),
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for event in stream:
            if event.type == "content_block_delta" and event.delta.type == "text_delta":
                yield event.delta.text


def _extract_json(text: str) -> dict | list:
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:]
        s = s.strip()
    first_obj = s.find("{")
    first_arr = s.find("[")
    candidates = [i for i in (first_obj, first_arr) if i != -1]
    if not candidates:
        raise ValueError("model did not return JSON")
    start = min(candidates)
    # Walk to the matching close. JSON allows nested so track depth.
    depth = 0
    in_str = False
    esc = False
    opener = s[start]
    closer = "}" if opener == "{" else "]"
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return json.loads(s[start : i + 1])
    raise ValueError("could not find balanced JSON in model output")
