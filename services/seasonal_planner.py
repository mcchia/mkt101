"""Seasonal campaign planner.

Calendar-aware plans for recurring seasons relevant to a Vietnamese
middle-to-high-end tea brand: Tet, Mid-Autumn, corporate gifting season,
holiday gift boxes, wellness gifting periods.

Stores plans so they can be re-opened and connected to the content calendar.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

from . import brand_memory, content_history, storage
from .llm import run_json

_STORE = "seasonal_plans"

SEASON_PRESETS: dict[str, dict[str, str]] = {
    "tet": {
        "label": "Tet (Lunar New Year)",
        "typical_window": "Mid-Dec to early-Feb (peak 2-3 weeks before Tet)",
        "notes": "Family, ancestry, tradition, premium gifting. Avoid cheap promo tone.",
    },
    "mid_autumn": {
        "label": "Mid-Autumn Festival",
        "typical_window": "3-4 weeks before the 15th day of the 8th lunar month",
        "notes": "Family reunion, moon-themed, pairing with mooncakes. Keep tasteful.",
    },
    "corporate_gifting": {
        "label": "Corporate gifting season",
        "typical_window": "Nov to mid-Jan; secondary window in spring",
        "notes": "B2B, tasteful presentation, bulk custom options, premium unboxing.",
    },
    "holiday_gift_boxes": {
        "label": "Holiday gift boxes (Dec)",
        "typical_window": "Early-Nov to late-Dec",
        "notes": "Gift boxes and curated bundles; quiet, elegant tone over hype.",
    },
    "wellness_gifting": {
        "label": "Wellness gifting",
        "typical_window": "Late-Dec (New Year resets), spring, late-summer",
        "notes": "Calm, ritual, balance. Never make medical claims.",
    },
}


@dataclass
class SeasonalPlan:
    id: str
    season_key: str
    season_label: str
    objective: str
    timing_window: str
    audience: str
    product_focus: str
    plan: dict[str, Any]
    created_at: int


_SYSTEM_EXTRA = """## Seasonal plan generation

Produce a calendar-aware plan for a premium tea brand. Keep the tone elegant
and never generic holiday spam. Respect brand memory and premium guardrails.
No medical claims. No discount-led framing. Use Facebook + Instagram.

Respond with JSON only:
{
  "headline_narrative": "...",
  "audience_summary": "...",
  "timeline": [
    {"phase": "teaser|launch|reinforce|close", "window": "...", "focus": "...",
     "posts": [
        {"channel": "instagram|facebook|both", "format": "...", "hook": "...",
         "angle": "...", "cta": "...", "pillar": "...", "kpi": "..."}
     ]}
  ],
  "risks_to_avoid": ["..."],
  "connect_to_calendar_notes": "..."
}
"""


def _load_all() -> list[dict[str, Any]]:
    data = storage.load(_STORE, [])
    return data if isinstance(data, list) else []


def list_plans() -> list[SeasonalPlan]:
    out: list[SeasonalPlan] = []
    for raw in _load_all():
        try:
            out.append(
                SeasonalPlan(
                    id=str(raw["id"]),
                    season_key=str(raw.get("season_key", "")),
                    season_label=str(raw.get("season_label", "")),
                    objective=str(raw.get("objective", "")),
                    timing_window=str(raw.get("timing_window", "")),
                    audience=str(raw.get("audience", "")),
                    product_focus=str(raw.get("product_focus", "")),
                    plan=raw.get("plan") or {},
                    created_at=int(raw.get("created_at", 0)),
                )
            )
        except (KeyError, ValueError, TypeError):
            continue
    return out


def delete_plan(plan_id: str) -> bool:
    items = _load_all()
    new = [p for p in items if p.get("id") != plan_id]
    if len(new) == len(items):
        return False
    storage.save(_STORE, new)
    return True


def generate_plan(
    season_key: str,
    *,
    objective: str,
    timing_window: str,
    audience: str,
    product_focus: str,
) -> SeasonalPlan:
    if season_key not in SEASON_PRESETS:
        raise ValueError(f"unknown season_key: {season_key}")
    preset = SEASON_PRESETS[season_key]
    if not objective.strip() or not audience.strip():
        raise ValueError("objective and audience are required")

    bm = brand_memory.system_block()
    ch = content_history.system_block()
    extra = "\n\n".join(b for b in [bm, ch, _SYSTEM_EXTRA] if b)

    prompt = (
        f"Season: {preset['label']} ({season_key})\n"
        f"Typical window: {preset['typical_window']}\n"
        f"Notes: {preset['notes']}\n\n"
        f"Objective: {objective.strip()}\n"
        f"Timing window (actual): {timing_window.strip() or preset['typical_window']}\n"
        f"Audience: {audience.strip()}\n"
        f"Product focus: {product_focus.strip() or '(unspecified)'}\n\n"
        "Produce the JSON plan now."
    )
    raw = run_json(prompt, extra_system=extra, max_tokens=6000)
    if not isinstance(raw, dict):
        raise ValueError("unexpected plan shape")

    plan = SeasonalPlan(
        id=uuid.uuid4().hex[:12],
        season_key=season_key,
        season_label=preset["label"],
        objective=objective.strip(),
        timing_window=(timing_window or preset["typical_window"]).strip(),
        audience=audience.strip(),
        product_focus=product_focus.strip(),
        plan=raw,
        created_at=int(time.time()),
    )
    items = _load_all()
    items.append(plan.__dict__.copy())
    storage.save(_STORE, items)
    return plan
