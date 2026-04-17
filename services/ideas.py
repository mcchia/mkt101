"""Idea generation → critique/score → top-3 selection."""
from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from models import (
    BrandProfile,
    ContentIdea,
    IdeaCritique,
    IdeaScore,
    IdeaStatus,
)
from prompts import (
    CRITIQUE_SCHEMA,
    CRITIQUE_USER_TEMPLATE,
    IDEAS_SCHEMA,
    IDEAS_USER_TEMPLATE,
    TOP3_SCHEMA,
    TOP3_USER_TEMPLATE,
    render_brand_block,
    render_history_block,
)
from services.llm import LLMUsage, get_llm_client


def generate_ideas(
    analysis: dict[str, Any],
    brand: BrandProfile | None,
    recent_ideas: list[ContentIdea],
    goal: str,
) -> tuple[list[ContentIdea], LLMUsage]:
    client = get_llm_client()
    user_msg = IDEAS_USER_TEMPLATE.format(
        schema=json.dumps(IDEAS_SCHEMA, indent=2),
        goal=goal or "(none specified)",
        brand_block=render_brand_block(brand),
        history_block=render_history_block(recent_ideas),
        analysis_json=json.dumps(analysis, indent=2, ensure_ascii=False),
    )
    data, usage = client.complete_json(user_msg)
    batch_id = f"batch_{uuid4().hex[:10]}"
    ideas: list[ContentIdea] = []
    for row in data.get("ideas", []):
        ideas.append(
            ContentIdea(
                batch_id=batch_id,
                title=row.get("title", "").strip(),
                concept=row.get("concept", ""),
                objective=row.get("objective", ""),
                audience_angle=row.get("audience_angle", ""),
                platform=row.get("platform", "instagram"),
                format=row.get("format", ""),
                pillar=row.get("pillar"),
                why_now=row.get("why_now", ""),
                evidence_refs=row.get("evidence_refs", []),
                status=IdeaStatus.DRAFT,
            )
        )
    return ideas, usage


def critique_and_score(
    ideas: list[ContentIdea],
    brand: BrandProfile | None,
    recent_ideas: list[ContentIdea],
) -> tuple[list[ContentIdea], LLMUsage]:
    client = get_llm_client()
    payload = [
        {
            "id": i.id,
            "title": i.title,
            "concept": i.concept,
            "objective": i.objective,
            "audience_angle": i.audience_angle,
            "platform": i.platform,
            "format": i.format,
            "pillar": i.pillar,
            "why_now": i.why_now,
        }
        for i in ideas
    ]
    user_msg = CRITIQUE_USER_TEMPLATE.format(
        schema=json.dumps(CRITIQUE_SCHEMA, indent=2),
        brand_block=render_brand_block(brand),
        history_block=render_history_block(recent_ideas),
        ideas_json=json.dumps(payload, indent=2, ensure_ascii=False),
    )
    data, usage = client.complete_json(user_msg)

    by_id = {i.id: i for i in ideas}
    for row in data.get("critiques", []):
        idea = by_id.get(row.get("idea_id"))
        if not idea:
            continue
        s = row.get("score", {})
        idea.score = IdeaScore(
            brand_fit=float(s.get("brand_fit", 0)),
            audience_relevance=float(s.get("audience_relevance", 0)),
            engagement_potential=float(s.get("engagement_potential", 0)),
            conversion_support=float(s.get("conversion_support", 0)),
            originality=float(s.get("originality", 0)),
            production_ease=float(s.get("production_ease", 0)),
            premium_safety=float(s.get("premium_safety", 0)),
        )
        c = row.get("critique", {})
        idea.critique = IdeaCritique(
            likely_upside=c.get("likely_upside", ""),
            likely_weakness=c.get("likely_weakness", ""),
            risks=c.get("risks", []),
        )
        idea.touch()
    return list(by_id.values()), usage


def select_top3(
    ideas: list[ContentIdea],
    brand: BrandProfile | None,
) -> tuple[list[ContentIdea], LLMUsage]:
    client = get_llm_client()
    payload = [
        {
            "id": i.id,
            "title": i.title,
            "concept": i.concept,
            "objective": i.objective,
            "pillar": i.pillar,
            "platform": i.platform,
            "format": i.format,
            "score": i.score.model_dump(),
            "score_total": i.score.total(),
            "critique": i.critique.model_dump(),
        }
        for i in ideas
    ]
    user_msg = TOP3_USER_TEMPLATE.format(
        schema=json.dumps(TOP3_SCHEMA, indent=2),
        brand_block=render_brand_block(brand),
        scored_ideas_json=json.dumps(payload, indent=2, ensure_ascii=False),
    )
    data, usage = client.complete_json(user_msg)

    by_id = {i.id: i for i in ideas}
    # reset prior selections in this batch
    for i in ideas:
        i.selected_top3 = False
        i.top3_reason = None

    for row in data.get("top3", []):
        idea = by_id.get(row.get("idea_id"))
        if not idea:
            continue
        idea.selected_top3 = True
        reason_parts = [row.get("why_selected", "").strip()]
        beats = row.get("beats_rejected", [])
        if beats:
            reason_parts.append("Beats rejected:")
            for b in beats:
                reason_parts.append(
                    f"- vs {b.get('rejected_idea_id', '?')}: {b.get('reason', '')}"
                )
        failure = row.get("failure_modes", [])
        if failure:
            reason_parts.append("Failure modes:")
            reason_parts.extend(f"- {f}" for f in failure)
        primary = row.get("primary_kpi")
        if primary:
            reason_parts.append(f"Primary KPI: {primary}")
        idea.top3_reason = "\n".join(reason_parts).strip()
        idea.status = IdeaStatus.NEEDS_REVIEW
        idea.touch()

    return [i for i in ideas if i.selected_top3], usage
