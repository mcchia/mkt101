"""Competitor watch insights layer.

Combines manual competitor records + safe web fetch + LLM synthesis to surface:
- competitor content themes
- posting frequency signals
- offer styles
- visual patterns
- recurring campaign angles
- whitespace opportunities

Explicitly does NOT produce copy-paste-ready content from competitor material.
The output is strategic (what is crowded, where is whitespace) not tactical
copycat output.
"""

from __future__ import annotations

from typing import Any

from connectors.competitors import manual, web

from . import brand_memory
from .llm import run_json

_SYSTEM_EXTRA = """## Competitor whitespace analysis

You are analyzing competitor-public-content descriptions for a premium tea brand.
DO NOT produce copycat captions, hooks, or creative that mirror competitor output.
Instead produce strategic observations and whitespace opportunities.

Return JSON only:
{
  "competitor_summary": "...",
  "themes": ["..."],
  "offer_styles": ["..."],
  "visual_patterns": ["..."],
  "recurring_angles": ["..."],
  "crowded_themes": ["..."],
  "whitespace_opportunities": [
    {"opportunity": "...", "why_it_fits_us": "...", "risk": "..."}
  ],
  "do_not_copy_notes": "..."
}
"""


def synthesize_insights(competitor_id: str | None = None) -> dict[str, Any]:
    comps = manual.list_competitors()
    if competitor_id:
        comps = [c for c in comps if c.id == competitor_id]
    if not comps:
        return {
            "competitor_summary": "No competitors on file.",
            "themes": [],
            "offer_styles": [],
            "visual_patterns": [],
            "recurring_angles": [],
            "crowded_themes": [],
            "whitespace_opportunities": [],
            "do_not_copy_notes": "Set up competitors first.",
        }

    corpus_lines: list[str] = []
    for c in comps:
        corpus_lines.append(f"### {c.name}")
        if c.handles:
            corpus_lines.append(f"Handles: {', '.join(c.handles)}")
        if c.urls:
            corpus_lines.append(f"URLs: {', '.join(c.urls)}")
        if c.notes:
            corpus_lines.append(f"Notes: {c.notes}")
        for obs in c.observations[-10:]:
            corpus_lines.append(
                f"- Observation ({obs.get('source', 'manual')}): "
                f"themes={obs.get('themes')}; frequency={obs.get('frequency')}; "
                f"offer_style={obs.get('offer_style')}; visuals={obs.get('visual_patterns')}; "
                f"angles={obs.get('campaign_angles')}"
            )
        corpus_lines.append("")

    extra = brand_memory.system_block()
    if extra:
        extra = extra + "\n\n" + _SYSTEM_EXTRA
    else:
        extra = _SYSTEM_EXTRA

    prompt = (
        "Competitor corpus:\n\n" + "\n".join(corpus_lines) +
        "\n\nProduce JSON insights as specified. Remember: do NOT copy competitor content."
    )
    raw = run_json(prompt, extra_system=extra, max_tokens=4000)
    if not isinstance(raw, dict):
        return {"competitor_summary": "Model returned unexpected shape.", "themes": [], "offer_styles": [], "visual_patterns": [], "recurring_angles": [], "crowded_themes": [], "whitespace_opportunities": [], "do_not_copy_notes": ""}
    return raw


def capture_web_observation(competitor_id: str, url: str) -> dict[str, Any]:
    """Fetch a public page for a competitor and store it as an observation.

    Uses safe, conservative web fetch. Raises on errors.
    """
    fetched = web.fetch_public_text(url)
    snippet_text = fetched["text"]

    # Extremely light heuristic summarization to fill observation fields;
    # deeper interpretation happens in synthesize_insights at the user's request.
    themes = []
    lower = snippet_text.lower()
    for kw in ("gift", "organic", "ceremony", "matcha", "oolong", "pu'er", "sencha", "wellness", "bundle"):
        if kw in lower:
            themes.append(kw)

    offer_style = ""
    for needle in ("free shipping", "gift with purchase", "bundle", "subscription", "pre-order"):
        if needle in lower:
            offer_style = needle
            break

    return manual.add_observation(
        competitor_id,
        themes=themes,
        frequency="",
        offer_style=offer_style,
        visual_patterns="",
        campaign_angles=[fetched["title"]] if fetched["title"] else [],
        source="web",
        source_url=fetched["url"],
    )
