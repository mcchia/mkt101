"""Top-3 selection with explicit comparisons vs. rejected ideas."""
from __future__ import annotations


TOP3_SCHEMA = {
    "type": "object",
    "required": ["top3"],
    "properties": {
        "top3": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "required": [
                    "idea_id",
                    "why_selected",
                    "beats_rejected",
                    "primary_kpi",
                    "failure_modes",
                ],
                "properties": {
                    "idea_id": {"type": "string"},
                    "why_selected": {"type": "string"},
                    "beats_rejected": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["rejected_idea_id", "reason"],
                            "properties": {
                                "rejected_idea_id": {"type": "string"},
                                "reason": {"type": "string"},
                            },
                        },
                    },
                    "primary_kpi": {"type": "string"},
                    "failure_modes": {"type": "array", "items": {"type": "string"}},
                },
            },
        }
    },
}


TOP3_USER_TEMPLATE = """STEP: TOP 3 SELECTION.

Pick the 3 strongest ideas. Return ONLY JSON matching this schema (no prose):

{schema}

Selection rules:
- Do not pick three variations of the same concept. Optimize the top 3 as a weekly set that covers different pillars or objectives.
- Use the weighted scores as a strong prior, but overrule them if premium safety or brand fit is marginal.
- Give each top-3 idea at least 2 items in `beats_rejected`, each comparing to a specific rejected idea by ID and stating the concrete reason.
- `primary_kpi` is the single metric this post is most meant to move (e.g. "saves per reach", "IG DM replies", "product-page clicks").
- `failure_modes` lists the specific ways execution could destroy the idea's value.

{brand_block}

[SCORED IDEAS]
{scored_ideas_json}

Return the JSON object now."""
