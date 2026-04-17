"""Idea generation prompt (10-15 distinct ideas)."""
from __future__ import annotations


IDEAS_SCHEMA = {
    "type": "object",
    "required": ["ideas"],
    "properties": {
        "ideas": {
            "type": "array",
            "minItems": 10,
            "maxItems": 15,
            "items": {
                "type": "object",
                "required": [
                    "title",
                    "concept",
                    "objective",
                    "audience_angle",
                    "platform",
                    "format",
                    "pillar",
                    "why_now",
                    "evidence_refs",
                ],
                "properties": {
                    "title": {"type": "string"},
                    "concept": {"type": "string"},
                    "objective": {"type": "string"},
                    "audience_angle": {"type": "string"},
                    "platform": {
                        "type": "string",
                        "enum": ["instagram", "facebook", "both"],
                    },
                    "format": {"type": "string"},
                    "pillar": {"type": "string"},
                    "why_now": {"type": "string"},
                    "evidence_refs": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        }
    },
}


IDEAS_USER_TEMPLATE = """STEP: IDEA GENERATION.

Using the prior performance analysis below, generate 10 to 15 DISTINCT next-post ideas. Return ONLY a JSON object matching this schema (no prose):

{schema}

Rules:
- Each idea must be a genuine variant in angle, pillar, or format — not reworded duplicates.
- `why_now` must cite specific observations from the analysis (e.g. "pairing-reels outperformed single-product shots by ~3x in reach").
- `evidence_refs` are post IDs or signal names from the analysis that justify the idea.
- Objectives should vary across saves, shares, discovery, conversion support, UGC generation, community, education.
- Stay fully on-brand: premium, crafted, editorial. No discount mechanics, no trendy clichés, no health claims.
- Do not reuse hooks or angles listed in [RECENT IDEAS].
- Respect brand pillars, tone, and posting constraints.
- Spread ideas across Instagram and Facebook appropriately given the brand's platform mix.

Goal context: {goal}

{brand_block}

{history_block}

[PRIOR ANALYSIS JSON]
{analysis_json}

Return the JSON object now."""
