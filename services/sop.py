"""SOP + dashboard recommendation generation."""
from __future__ import annotations

import json
from typing import Any

from models import BrandProfile, ContentIdea
from prompts import SOP_SCHEMA, SOP_USER_TEMPLATE, render_brand_block
from services.llm import LLMUsage, get_llm_client


def generate_sop_and_dashboard(
    analysis: dict[str, Any],
    top3: list[ContentIdea],
    brand: BrandProfile | None,
) -> tuple[dict[str, Any], LLMUsage]:
    client = get_llm_client()
    top3_payload = [
        {
            "id": i.id,
            "title": i.title,
            "pillar": i.pillar,
            "platform": i.platform,
            "format": i.format,
            "top3_reason": i.top3_reason,
        }
        for i in top3
    ]
    user_msg = SOP_USER_TEMPLATE.format(
        schema=json.dumps(SOP_SCHEMA, indent=2),
        brand_block=render_brand_block(brand),
        analysis_json=json.dumps(analysis, indent=2, ensure_ascii=False),
        top3_json=json.dumps(top3_payload, indent=2, ensure_ascii=False),
    )
    data, usage = client.complete_json(user_msg)
    return data, usage
