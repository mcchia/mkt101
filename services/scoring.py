"""Scoring helpers that stay deterministic and don't touch the LLM."""
from __future__ import annotations

from models import ContentIdea, IdeaScore


def recompute_score_total(score: IdeaScore) -> float:
    return score.total()


def rank_ideas(ideas: list[ContentIdea]) -> list[ContentIdea]:
    return sorted(ideas, key=lambda i: i.score.total(), reverse=True)


def brief_score_summary(score: IdeaScore) -> str:
    return (
        f"brand_fit {score.brand_fit:.1f} | audience {score.audience_relevance:.1f} | "
        f"eng {score.engagement_potential:.1f} | conv {score.conversion_support:.1f} | "
        f"orig {score.originality:.1f} | ease {score.production_ease:.1f} | "
        f"premium {score.premium_safety:.1f} → {score.total():.2f}"
    )
