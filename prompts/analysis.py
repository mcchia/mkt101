"""Performance analysis prompt."""
from __future__ import annotations


ANALYSIS_SCHEMA = {
    "type": "object",
    "required": [
        "facts",
        "interpretations",
        "assumptions",
        "clarifying_questions",
        "working_signals",
        "failing_signals",
        "platform_notes",
        "data_quality_caveats",
    ],
    "properties": {
        "facts": {"type": "array", "items": {"type": "string"}},
        "interpretations": {"type": "array", "items": {"type": "string"}},
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "clarifying_questions": {"type": "array", "items": {"type": "string"}},
        "working_signals": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["signal", "evidence"],
                "properties": {
                    "signal": {"type": "string"},
                    "evidence": {"type": "string"},
                    "confidence": {"type": "string"},
                },
            },
        },
        "failing_signals": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["signal", "evidence"],
                "properties": {
                    "signal": {"type": "string"},
                    "evidence": {"type": "string"},
                    "confidence": {"type": "string"},
                },
            },
        },
        "platform_notes": {
            "type": "object",
            "properties": {
                "instagram": {"type": "string"},
                "facebook": {"type": "string"},
            },
        },
        "data_quality_caveats": {"type": "array", "items": {"type": "string"}},
    },
}


ANALYSIS_USER_TEMPLATE = """STEP: PERFORMANCE ANALYSIS.

You will analyze the performance data supplied below and return ONLY a JSON object matching this schema (no prose, no code fences):

{schema}

Rules specific to this step:
- `facts` must be directly observable from the data (numbers, counts, orderings). No interpretation.
- `interpretations` explain what the facts plausibly mean; each must cite at least one fact.
- `assumptions` are things you are asserting without evidence. Keep the list short and honest.
- `clarifying_questions` only go here if a missing piece would materially change the recommendation. 0 is fine.
- `working_signals` and `failing_signals` each get up to 5 items. `evidence` must reference specific post IDs or metric deltas from the data.
- `platform_notes` must separate Instagram and Facebook behavior when both are present.
- `data_quality_caveats` flags thin data, missing metrics, short time windows, etc.

Goal context (from user): {goal}

{brand_block}

{history_block}

{data_block}

Return the JSON object now."""
