"""Reusable workflow templates.

Each template is a prefilled prompt scaffold for a recurring task. Templates
respect brand memory and premium guardrails. Users can customize and save
their own variants without touching code.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

from . import brand_memory, content_history, patterns, losing_posts, storage

_STORE = "templates"


@dataclass
class Template:
    id: str
    key: str  # stable key for the built-in template (or "custom")
    name: str
    description: str
    prompt: str
    output_sections: list[str]
    built_in: bool = False
    created_at: int = 0


# Built-in template library. Prompts are deliberately concrete and reference
# brand memory, recent history, and winning/losing patterns so the main
# marketing system prompt can synthesise consistent output.
BUILT_INS: list[Template] = [
    Template(
        id="builtin-weekly",
        key="weekly_analysis",
        name="Weekly analysis",
        description="Review the last 7 days of Facebook + Instagram performance and output next-week actions.",
        prompt=(
            "Run a weekly analysis for the last 7 days of Facebook and Instagram content.\n\n"
            "Use brand memory, recent content history, and winning/losing patterns as context.\n\n"
            "Deliverables:\n"
            "1. Performance summary (what actually happened, not a stats dump)\n"
            "2. What worked vs. what did not, with evidence strength labels\n"
            "3. 3 decisions for next week (keep / adjust / stop)\n"
            "4. 5-7 specific post ideas that avoid recent repetition\n"
            "5. 1 brand-risk watchout\n"
        ),
        output_sections=[
            "Performance summary",
            "What worked vs. did not",
            "Next-week decisions",
            "Post ideas",
            "Brand-risk watchout",
        ],
        built_in=True,
    ),
    Template(
        id="builtin-monthly",
        key="monthly_review",
        name="Monthly review",
        description="30-day structural review with pillar balance, fatigue, and quarterly direction.",
        prompt=(
            "Produce a 30-day review.\n\nDeliverables:\n"
            "1. Pillar balance check vs. brand content pillars\n"
            "2. Fatigue signals (hooks, angles, CTAs, formats)\n"
            "3. Winning patterns to double down on (only where evidence is strong)\n"
            "4. Losing patterns to stop/reduce/retest with reasons\n"
            "5. Draft direction for the next 30 days\n"
            "6. One KPI to focus on and why\n"
        ),
        output_sections=[
            "Pillar balance",
            "Fatigue signals",
            "Winning patterns",
            "Losing patterns",
            "Next 30 days",
            "Focus KPI",
        ],
        built_in=True,
    ),
    Template(
        id="builtin-campaign",
        key="campaign_kickoff",
        name="Campaign kickoff",
        description="Structured kickoff for a new campaign: objective, audience, offer, message spine, content plan.",
        prompt=(
            "You are kicking off a campaign. Ask for the minimum missing inputs first "
            "(objective, audience slice, offer, timing window). Once you have them, "
            "produce:\n"
            "1. Campaign objective and KPI\n"
            "2. Message spine (one-sentence core idea that stays premium)\n"
            "3. 3 content angles with justification\n"
            "4. Content calendar outline (teaser -> launch -> reinforce -> close)\n"
            "5. Asset requirements and CTAs\n"
            "6. Brand-risk checks\n"
        ),
        output_sections=[
            "Objective + KPI",
            "Message spine",
            "Content angles",
            "Calendar outline",
            "Assets + CTAs",
            "Brand-risk checks",
        ],
        built_in=True,
    ),
    Template(
        id="builtin-product-launch",
        key="product_launch",
        name="Product launch",
        description="Launch plan for a new tea product, staged over teaser/launch/post-launch.",
        prompt=(
            "Plan a product launch for a new tea SKU. Assume a premium positioning.\n\n"
            "Deliverables:\n"
            "1. Positioning one-liner (no hype, no discount lead)\n"
            "2. Pre-launch teaser plan (3-5 posts)\n"
            "3. Launch-day plan (Instagram + Facebook variants)\n"
            "4. Post-launch reinforcement plan (2 weeks)\n"
            "5. CTA ladder (soft -> direct) consistent with premium tone\n"
            "6. KPIs at each stage\n"
        ),
        output_sections=[
            "Positioning",
            "Teaser plan",
            "Launch day",
            "Reinforcement",
            "CTA ladder",
            "KPIs",
        ],
        built_in=True,
    ),
    Template(
        id="builtin-gifting",
        key="gifting_season",
        name="Gifting season plan",
        description="Corporate + personal gifting plan for a defined gifting window.",
        prompt=(
            "Build a gifting-season plan for the specified window. Confirm the window "
            "and primary audience (personal vs corporate) first, then produce:\n"
            "1. Gifting narrative (premium, tasteful, not discount-led)\n"
            "2. Bundle/SKU suggestions appropriate for gifting\n"
            "3. 6-8 post ideas across the window\n"
            "4. Packaging / presentation hints that reinforce premium perception\n"
            "5. CTA language that fits gifting (reserve, pre-order, custom notes)\n"
            "6. Risks to avoid (cheap promo tone, urgency overkill)\n"
        ),
        output_sections=[
            "Gifting narrative",
            "Bundles/SKUs",
            "Post ideas",
            "Packaging hints",
            "CTA language",
            "Risks to avoid",
        ],
        built_in=True,
    ),
]


def _load_custom() -> list[dict[str, Any]]:
    data = storage.load(_STORE, [])
    return data if isinstance(data, list) else []


def list_all() -> list[Template]:
    customs: list[Template] = []
    for raw in _load_custom():
        try:
            customs.append(
                Template(
                    id=str(raw["id"]),
                    key=str(raw.get("key", "custom")),
                    name=str(raw.get("name", "Untitled")),
                    description=str(raw.get("description", "")),
                    prompt=str(raw.get("prompt", "")),
                    output_sections=list(raw.get("output_sections", [])),
                    built_in=False,
                    created_at=int(raw.get("created_at", 0)),
                )
            )
        except (KeyError, ValueError, TypeError):
            continue
    return list(BUILT_INS) + customs


def get(template_id: str) -> Template | None:
    for t in list_all():
        if t.id == template_id:
            return t
    return None


def save_custom(name: str, description: str, prompt: str, output_sections: list[str]) -> Template:
    if not name.strip() or not prompt.strip():
        raise ValueError("name and prompt are required")
    tpl = Template(
        id="custom-" + uuid.uuid4().hex[:10],
        key="custom",
        name=name.strip(),
        description=description.strip(),
        prompt=prompt.strip(),
        output_sections=[s.strip() for s in output_sections if s.strip()],
        built_in=False,
        created_at=int(time.time()),
    )
    items = _load_custom()
    items.append(tpl.__dict__.copy())
    storage.save(_STORE, items)
    return tpl


def delete_custom(template_id: str) -> bool:
    items = _load_custom()
    new = [r for r in items if r.get("id") != template_id]
    if len(new) == len(items):
        return False
    storage.save(_STORE, new)
    return True


def assemble_prompt(template: Template, user_notes: str = "") -> tuple[str, str]:
    """Return (user_prompt, extra_system) that respects brand/history/patterns."""
    extra_bits: list[str] = []
    bm = brand_memory.system_block()
    if bm:
        extra_bits.append(bm)
    ch = content_history.system_block()
    if ch:
        extra_bits.append(ch)
    tp = patterns.system_block()
    if tp:
        extra_bits.append(tp)
    lp = losing_posts.system_block()
    if lp:
        extra_bits.append(lp)
    extra_system = "\n\n".join(extra_bits)

    prompt = template.prompt.strip()
    if user_notes.strip():
        prompt += "\n\nAdditional user notes:\n" + user_notes.strip()
    if template.output_sections:
        prompt += "\n\nUse these output section headings:\n- " + "\n- ".join(
            template.output_sections
        )
    return prompt, extra_system
