"""Core system prompt and context block renderers.

The system prompt is deliberately long and stable so it stays in the prompt
cache across turns. Dynamic brand, data, and history context is rendered
separately and appended as the user message.
"""
from __future__ import annotations

import json
from typing import Iterable

from models import BrandProfile, ContentIdea, Post


CORE_SYSTEM = """You are the in-house AI Marketing Operator for a middle- to high-end tea e-commerce brand. You work alongside the founder, internal marketing team, and executives. Your output is consumed inside an internal operator dashboard, not published directly to customers.

## Non-negotiable operating rules

1. Separate FACTS, INTERPRETATIONS, ASSUMPTIONS, and RECOMMENDATIONS in every analysis. Never let one bleed into another.
2. Do not hallucinate data, customer behavior, benchmarks, or performance explanations. If you do not know, say so.
3. Label every assumption explicitly. Assumptions are cheap; disguised assumptions are dangerous.
4. Ask high-value clarifying questions only when the missing information materially changes the recommendation. Otherwise proceed and flag uncertainty.
5. Protect premium brand positioning at all costs. Reject any idea that is discount-heavy, cheap, noisy, childish, mass-market, trend-chasing for its own sake, or health-claim-y.
6. Distinguish reach, engagement (likes/reactions/comments), saves, shares, clicks, and conversions. Do not optimize vanity metrics at the expense of business outcomes.
7. Instagram and Facebook are different. Instagram favors reels, visual aesthetics, saves, and shares as intent signal. Facebook favors longer captions, community discussion, and link clicks.
8. Be concise. No fluff, no generic marketing advice, no cliched phrases like "engaging content" or "this could resonate" without a reason.
9. Do not repeat hooks, angles, or formats that already appear in the recent content history the user has shared.
10. Output JSON when asked to, and only JSON — no prose, no code fences around the JSON, no commentary. When asked for prose, return prose.

## Premium brand guardrails you must enforce

- No percentage-off language as the primary hook.
- No clickbait hooks, no fake scarcity, no shock tactics.
- No meme formats that clash with the quiet, crafted brand tone.
- No unverified health or medical claims about tea.
- No AI-visible clichés ("unlock the secret", "level up", "game-changer", "must-have").
- Originality and craft language beat trend-chasing.

## Your structured workflow

Depending on which step the user invokes, you will:
- analyze recent social performance
- generate 10-15 distinct content ideas
- critique and score each idea against a transparent rubric
- select exactly 3 top ideas and explain why each beat the rejected ones
- produce execution briefs
- produce SOP / dashboard recommendations

You will always be told which step to perform and what JSON schema to return.
"""


def render_brand_block(brand: BrandProfile | None) -> str:
    if not brand or not brand.brand_name:
        return "[BRAND PROFILE] (not yet configured — treat as middle-to-high-end tea brand, premium positioning)"

    pillars = ", ".join(p.name for p in brand.content_pillars) or "(none set)"
    constraints = brand.posting_constraints
    lines = [
        "[BRAND PROFILE]",
        f"- Name: {brand.brand_name}",
        f"- Website: {brand.website or '(none)'}",
        f"- One-liner: {brand.one_liner or '(none)'}",
        f"- Positioning: {brand.positioning or '(none)'}",
        f"- Price tier: {brand.price_tier}",
        f"- Target audience: {brand.target_audience or '(none)'}",
        f"- Tone of voice: {brand.tone_of_voice or '(none)'}",
        f"- Brand values: {', '.join(brand.brand_values) or '(none)'}",
        f"- Signature products: {', '.join(brand.signature_products) or '(none)'}",
        f"- Content pillars: {pillars}",
        f"- Max posts/week: {constraints.max_posts_per_week}",
        f"- Preferred platforms: {', '.join(constraints.preferred_platforms)}",
        f"- Avoid topics: {', '.join(constraints.avoid_topics) or '(none)'}",
        f"- Forbidden hooks: {', '.join(brand.forbidden_hooks) or '(none)'}",
        "- Guardrails:",
        *(f"  - {g}" for g in brand.premium_guardrails),
    ]
    return "\n".join(lines)


def render_history_block(recent_ideas: Iterable[ContentIdea]) -> str:
    lines = ["[RECENT IDEAS / HOOKS ALREADY USED — DO NOT REPEAT]"]
    any_added = False
    for idea in recent_ideas:
        any_added = True
        lines.append(f"- {idea.title} ({idea.format}) — pillar: {idea.pillar or 'n/a'}")
    if not any_added:
        lines.append("(no prior ideas recorded)")
    return "\n".join(lines)


def render_data_block(posts: Iterable[Post]) -> str:
    """Render posts as a compact, auditable performance table."""
    rows = list(posts)
    if not rows:
        return "[PERFORMANCE DATA]\n(no post-level data supplied)"

    header = [
        "id",
        "platform",
        "created",
        "media",
        "pillar",
        "format",
        "reach",
        "impr",
        "likes",
        "comm",
        "shares",
        "saves",
        "clicks",
        "conv",
        "caption",
    ]
    lines = ["[PERFORMANCE DATA]", "\t".join(header)]
    for p in rows:
        m = p.metrics
        caption = (p.caption or "").replace("\t", " ").replace("\n", " ")
        if len(caption) > 140:
            caption = caption[:139] + "…"
        lines.append(
            "\t".join(
                [
                    p.id,
                    p.platform.value,
                    p.created_at.date().isoformat() if p.created_at else "",
                    p.media_type.value,
                    p.pillar or "",
                    p.format_label or "",
                    str(m.reach) if m.reach is not None else "",
                    str(m.impressions) if m.impressions is not None else "",
                    str(m.likes) if m.likes is not None else "",
                    str(m.comments) if m.comments is not None else "",
                    str(m.shares) if m.shares is not None else "",
                    str(m.saves) if m.saves is not None else "",
                    str(m.clicks) if m.clicks is not None else "",
                    str(m.conversions) if m.conversions is not None else "",
                    caption,
                ]
            )
        )
    return "\n".join(lines)


def render_site_snippets(records: Iterable[dict], limit: int = 15) -> str:
    rows = list(records)[:limit]
    if not rows:
        return "[SITE / PRODUCT CONTEXT]\n(no crawled pages supplied)"
    out = ["[SITE / PRODUCT CONTEXT — use as brand grounding, not verbatim copy]"]
    for r in rows:
        out.append(json.dumps(r, ensure_ascii=False, default=str))
    return "\n".join(out)
