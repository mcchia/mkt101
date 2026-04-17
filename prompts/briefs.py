"""Execution brief prompt, per selected idea."""
from __future__ import annotations


BRIEF_SCHEMA = {
    "type": "object",
    "required": ["brief"],
    "properties": {
        "brief": {
            "type": "object",
            "required": [
                "hook",
                "angle",
                "draft_caption",
                "creative_direction",
                "asset_requirements",
                "cta",
                "platform_fit",
                "kpis_to_monitor",
                "failure_modes",
            ],
            "properties": {
                "hook": {"type": "string"},
                "angle": {"type": "string"},
                "draft_caption": {"type": "string"},
                "creative_direction": {"type": "string"},
                "asset_requirements": {"type": "array", "items": {"type": "string"}},
                "cta": {"type": "string"},
                "platform_fit": {"type": "array", "items": {"type": "string"}},
                "recommended_order": {"type": ["integer", "null"]},
                "kpis_to_monitor": {"type": "array", "items": {"type": "string"}},
                "failure_modes": {"type": "array", "items": {"type": "string"}},
            },
        }
    },
}


BRIEF_USER_TEMPLATE = """STEP: EXECUTION BRIEF.

Produce a production-ready brief for the single idea below. Return ONLY JSON matching this schema:

{schema}

Brief rules:
- `hook`: the first 1-2 lines of the caption or the on-screen opener for video. Editorial, crafted, no clichés.
- `draft_caption`: full caption, calibrated to the target platform. Tea-literate, premium voice. No emoji walls.
- `creative_direction`: describe shots, pacing, lighting, prop styling in 3-6 sentences.
- `asset_requirements`: concrete list (e.g. "one 30s vertical reel", "3 still images 4:5", "ceramic prop — dark clay").
- `cta`: a single, specific CTA. Quiet confidence beats urgency.
- `platform_fit`: which of ["instagram", "facebook"] this should run on; include both only if it genuinely fits both.
- `kpis_to_monitor`: the 2-3 most relevant KPIs for this post's objective.
- `failure_modes`: specific ways this could flop if executed badly.

{brand_block}

[IDEA]
{idea_json}

Return the JSON object now."""
