"""Execution brief generation."""
from __future__ import annotations

import json

from models import BrandProfile, ContentIdea, ExecutionBrief
from prompts import BRIEF_SCHEMA, BRIEF_USER_TEMPLATE, render_brand_block
from services.llm import LLMUsage, get_llm_client


def generate_execution_brief(
    idea: ContentIdea,
    brand: BrandProfile | None,
) -> tuple[ExecutionBrief, LLMUsage]:
    client = get_llm_client()
    idea_payload = {
        "id": idea.id,
        "title": idea.title,
        "concept": idea.concept,
        "objective": idea.objective,
        "audience_angle": idea.audience_angle,
        "platform": idea.platform,
        "format": idea.format,
        "pillar": idea.pillar,
        "why_now": idea.why_now,
        "critique": idea.critique.model_dump(),
        "top3_reason": idea.top3_reason,
    }
    user_msg = BRIEF_USER_TEMPLATE.format(
        schema=json.dumps(BRIEF_SCHEMA, indent=2),
        brand_block=render_brand_block(brand),
        idea_json=json.dumps(idea_payload, indent=2, ensure_ascii=False),
    )
    data, usage = client.complete_json(user_msg)
    b = data.get("brief", {})
    brief = ExecutionBrief(
        hook=b.get("hook", ""),
        angle=b.get("angle", ""),
        draft_caption=b.get("draft_caption", ""),
        creative_direction=b.get("creative_direction", ""),
        asset_requirements=b.get("asset_requirements", []),
        cta=b.get("cta", ""),
        platform_fit=b.get("platform_fit", []),
        recommended_order=b.get("recommended_order"),
        kpis_to_monitor=b.get("kpis_to_monitor", []),
        failure_modes=b.get("failure_modes", []),
    )
    idea.brief = brief
    idea.touch()
    return brief, usage
