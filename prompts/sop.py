"""SOP + dashboard logic recommendations."""
from __future__ import annotations


SOP_SCHEMA = {
    "type": "object",
    "required": ["weekly_sop", "dashboard_questions", "repeat", "stop", "test_next"],
    "properties": {
        "weekly_sop": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["day", "step"],
                "properties": {
                    "day": {"type": "string"},
                    "step": {"type": "string"},
                    "owner": {"type": "string"},
                    "output": {"type": "string"},
                },
            },
        },
        "dashboard_questions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["question", "metric", "reading_guide"],
                "properties": {
                    "question": {"type": "string"},
                    "metric": {"type": "string"},
                    "reading_guide": {"type": "string"},
                },
            },
        },
        "repeat": {"type": "array", "items": {"type": "string"}},
        "stop": {"type": "array", "items": {"type": "string"}},
        "test_next": {"type": "array", "items": {"type": "string"}},
    },
}


SOP_USER_TEMPLATE = """STEP: SOP + DASHBOARD LOGIC.

Produce a weekly operating SOP and a dashboard-reading guide. Return ONLY JSON matching this schema:

{schema}

Rules:
- `weekly_sop`: 5-8 items, each anchored to a weekday, with an owner role and concrete output.
- `dashboard_questions`: 5-8 specific questions the dashboard should answer (e.g. "Which pillar drove the most saves per reach this week?"). For each, name the exact metric and give a 1-sentence `reading_guide` on how to interpret good vs bad movement.
- `repeat`: what this brand should keep doing based on the supplied analysis.
- `stop`: what this brand should stop doing based on the supplied analysis.
- `test_next`: 3-5 tests worth running next week, specific and measurable.
- Keep everything grounded in the analysis provided. Do not invent generic marketing advice.

{brand_block}

[ANALYSIS]
{analysis_json}

[TOP 3 DECISIONS]
{top3_json}

Return the JSON object now."""
