"""A/B test planning.

Given a selected concept, produce exactly two on-brand variants that differ on
a named dimension (hook / caption / format / CTA). The output clearly labels:
- what is changing between A and B
- the KPI the test is intended to learn from
- premium-positioning guardrails
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from . import brand_memory, storage
from .llm import run_json

_STORE = "ab_tests"

DIMENSIONS = ["hook", "caption", "format", "cta"]

_SYSTEM_EXTRA = """## A/B variant generation

You will produce exactly two variants (A and B) for the supplied concept.
- Only the specified dimension may differ meaningfully. Keep the rest consistent.
- Both variants must remain on-brand for a middle-to-high-end tea shop.
- State what is changing in one sentence.
- State the single KPI this test is designed to learn from.
- Never use banned phrases from brand memory.
- Never produce cheap, hypey, mass-market, or discount-led variants.

Respond with JSON only, no prose, matching this schema:
{
  "concept": "...",
  "dimension": "hook|caption|format|cta",
  "what_is_changing": "...",
  "kpi": "...",
  "variant_a": {"label": "A", "hook": "...", "caption": "...", "format": "...", "cta": "..."},
  "variant_b": {"label": "B", "hook": "...", "caption": "...", "format": "...", "cta": "..."},
  "guardrail_notes": "..."
}
"""


def _load() -> list[dict[str, Any]]:
    data = storage.load(_STORE, [])
    return data if isinstance(data, list) else []


def _save(items: list[dict[str, Any]]) -> None:
    storage.save(_STORE, items)


def list_plans() -> list[dict[str, Any]]:
    return _load()


def delete_plan(plan_id: str) -> bool:
    items = _load()
    new = [p for p in items if p.get("id") != plan_id]
    if len(new) == len(items):
        return False
    _save(new)
    return True


def generate_plan(concept: str, dimension: str, context: str = "") -> dict[str, Any]:
    if dimension not in DIMENSIONS:
        raise ValueError(f"dimension must be one of {DIMENSIONS}")
    if not concept.strip():
        raise ValueError("concept cannot be empty")

    prompt = (
        f"Concept:\n{concept.strip()}\n\n"
        f"Dimension to vary between A and B: {dimension}\n\n"
        f"Additional context (may be empty):\n{context.strip() or '(none)'}\n\n"
        "Produce JSON only as specified."
    )
    extra = brand_memory.system_block()
    if extra:
        extra = extra + "\n\n" + _SYSTEM_EXTRA
    else:
        extra = _SYSTEM_EXTRA

    raw = run_json(prompt, extra_system=extra, max_tokens=4000)
    if not isinstance(raw, dict):
        raise ValueError("unexpected A/B response shape")

    plan = {
        "id": uuid.uuid4().hex[:12],
        "created_at": int(time.time()),
        "concept": concept.strip(),
        "dimension": dimension,
        "context": context.strip(),
        "plan": raw,
    }
    items = _load()
    items.append(plan)
    _save(items)
    return plan
