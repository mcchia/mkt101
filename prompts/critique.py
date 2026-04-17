"""Critique + scoring prompt. Scores every idea on the 7-dim rubric."""
from __future__ import annotations


CRITIQUE_SCHEMA = {
    "type": "object",
    "required": ["critiques"],
    "properties": {
        "critiques": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["idea_id", "score", "critique"],
                "properties": {
                    "idea_id": {"type": "string"},
                    "score": {
                        "type": "object",
                        "required": [
                            "brand_fit",
                            "audience_relevance",
                            "engagement_potential",
                            "conversion_support",
                            "originality",
                            "production_ease",
                            "premium_safety",
                        ],
                        "properties": {
                            "brand_fit": {"type": "number", "minimum": 0, "maximum": 10},
                            "audience_relevance": {"type": "number", "minimum": 0, "maximum": 10},
                            "engagement_potential": {"type": "number", "minimum": 0, "maximum": 10},
                            "conversion_support": {"type": "number", "minimum": 0, "maximum": 10},
                            "originality": {"type": "number", "minimum": 0, "maximum": 10},
                            "production_ease": {"type": "number", "minimum": 0, "maximum": 10},
                            "premium_safety": {"type": "number", "minimum": 0, "maximum": 10},
                        },
                    },
                    "critique": {
                        "type": "object",
                        "required": ["likely_upside", "likely_weakness", "risks"],
                        "properties": {
                            "likely_upside": {"type": "string"},
                            "likely_weakness": {"type": "string"},
                            "risks": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
            },
        }
    },
}


CRITIQUE_USER_TEMPLATE = """STEP: CRITIQUE + SCORE.

Score every idea below on the 7-dimension rubric (0-10 floats, 0.5 increments OK) and return critiques. Return ONLY JSON matching this schema (no prose):

{schema}

Rubric definitions — use these literally:
- brand_fit: alignment with the brand's positioning, values, tone, and pillars.
- audience_relevance: how directly this speaks to the stated target audience.
- engagement_potential: realistic chance of saves/shares/comments given the format & hook.
- conversion_support: how well it supports buying intent or DM/visit behavior (indirectly is fine).
- originality: novelty vs. the category and vs. the brand's own history.
- production_ease: lower friction to produce = higher score. 10 = a founder can film in 20 minutes.
- premium_safety: how safe this is for premium perception. A 10 cannot be misread as cheap, noisy, or mass-market. A 0 would actively erode premium positioning.

Critical rules:
- Penalize hard on `premium_safety` and `brand_fit` for anything discount-led, loud, clichéd, gimmicky, health-claim-y, or childish.
- Penalize `originality` for anything close to an idea in [RECENT IDEAS].
- Do NOT round toward the middle. Differentiate the ideas.
- Keep `likely_upside` and `likely_weakness` to one tight sentence each. No fluff.

{brand_block}

{history_block}

[IDEAS TO SCORE]
{ideas_json}

Return the JSON object now."""
