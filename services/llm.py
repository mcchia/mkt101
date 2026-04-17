"""LLM client wrapper.

Centralizes: cached system prompt, structured JSON extraction, token usage
accounting, and consistent error handling. Every other service calls into
this module instead of the Anthropic SDK directly.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable, Optional

import anthropic

from config import get_settings
from prompts import CORE_SYSTEM
from utils.logging import get_logger, log_event


class LLMError(RuntimeError):
    pass


@dataclass
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_write: int = 0


@dataclass
class LLMResult:
    text: str
    usage: LLMUsage


_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def _strip_fences(text: str) -> str:
    match = _JSON_FENCE_RE.match(text.strip())
    return match.group(1) if match else text


def _extract_json(text: str) -> Any:
    """Parse JSON robustly. If the model wrapped it in prose/fences, recover."""
    cleaned = _strip_fences(text.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # last-ditch: grab the widest balanced {...} or [...] span
    for opener, closer in [("{", "}"), ("[", "]")]:
        start = cleaned.find(opener)
        end = cleaned.rfind(closer)
        if start != -1 and end != -1 and end > start:
            snippet = cleaned[start : end + 1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                continue
    raise LLMError(f"Could not parse JSON from model output: {text[:400]}")


class LLMClient:
    def __init__(self, api_key: str, model: str, max_tokens: int) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens
        self._logger = get_logger("mkt101.llm")

    @property
    def model(self) -> str:
        return self._model

    def complete(
        self,
        user_content: str,
        *,
        on_text: Optional[Callable[[str], None]] = None,
        temperature: Optional[float] = None,
    ) -> LLMResult:
        """Stream a completion with the cached core system prompt."""

        # The core system prompt is long and stable — cache it.
        kwargs: dict[str, Any] = dict(
            model=self._model,
            max_tokens=self._max_tokens,
            system=[
                {
                    "type": "text",
                    "text": CORE_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            messages=[{"role": "user", "content": user_content}],
        )
        if temperature is not None:
            kwargs["temperature"] = temperature

        parts: list[str] = []
        try:
            with self._client.messages.stream(**kwargs) as stream:
                for event in stream:
                    if event.type == "content_block_delta" and event.delta.type == "text_delta":
                        parts.append(event.delta.text)
                        if on_text:
                            try:
                                on_text(event.delta.text)
                            except Exception:
                                # never let UI callbacks kill the stream
                                pass
                final = stream.get_final_message()
        except anthropic.APIError as e:
            log_event("llm_api_error", model=self._model, error=str(e))
            raise LLMError(f"Anthropic API error: {e}") from e

        usage = final.usage
        result = LLMResult(
            text="".join(parts),
            usage=LLMUsage(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_read=getattr(usage, "cache_read_input_tokens", 0) or 0,
                cache_write=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            ),
        )
        log_event(
            "llm_complete",
            model=self._model,
            in_tokens=result.usage.input_tokens,
            out_tokens=result.usage.output_tokens,
            cache_read=result.usage.cache_read,
            cache_write=result.usage.cache_write,
        )
        return result

    def complete_json(self, user_content: str, **kwargs: Any) -> tuple[Any, LLMUsage]:
        result = self.complete(user_content, **kwargs)
        return _extract_json(result.text), result.usage


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise LLMError("ANTHROPIC_API_KEY is not set.")
    return LLMClient(
        api_key=settings.anthropic_api_key,
        model=settings.model,
        max_tokens=settings.max_output_tokens,
    )
