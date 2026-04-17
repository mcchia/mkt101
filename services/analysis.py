"""Performance analysis orchestration."""
from __future__ import annotations

import json
from typing import Any

from models import BrandProfile, ContentIdea, Post
from prompts import (
    ANALYSIS_SCHEMA,
    ANALYSIS_USER_TEMPLATE,
    render_brand_block,
    render_data_block,
    render_history_block,
)
from services.llm import LLMUsage, get_llm_client


def run_performance_analysis(
    posts: list[Post],
    brand: BrandProfile | None,
    recent_ideas: list[ContentIdea],
    goal: str,
) -> tuple[dict[str, Any], LLMUsage]:
    client = get_llm_client()
    user_msg = ANALYSIS_USER_TEMPLATE.format(
        schema=json.dumps(ANALYSIS_SCHEMA, indent=2),
        goal=goal or "(none specified)",
        brand_block=render_brand_block(brand),
        history_block=render_history_block(recent_ideas),
        data_block=render_data_block(posts),
    )
    return client.complete_json(user_msg)
