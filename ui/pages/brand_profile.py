"""Brand profile editor — persists to repo.get_brand()."""
from __future__ import annotations

import streamlit as st

from models import BrandProfile, ContentPillar, PostingConstraint
from storage import get_repository


def _split_lines(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]


def render() -> None:
    st.header("Brand Profile")
    st.caption(
        "Stable memory the assistant reads every call. "
        "Complete this first — it's the single biggest lever on output quality."
    )

    repo = get_repository()
    brand = repo.get_brand() or BrandProfile()

    with st.form("brand_profile_form", clear_on_submit=False):
        cols = st.columns(2)
        brand.brand_name = cols[0].text_input("Brand name", value=brand.brand_name)
        brand.website = cols[1].text_input("Website", value=brand.website)

        brand.one_liner = st.text_input(
            "One-liner",
            value=brand.one_liner,
            help="How you'd describe the brand in one sentence.",
        )
        brand.positioning = st.text_area(
            "Positioning",
            value=brand.positioning,
            height=90,
            help="What shelf you sit on. Who you're not.",
        )

        cols = st.columns(2)
        brand.price_tier = cols[0].text_input("Price tier", value=brand.price_tier)
        brand.target_audience = cols[1].text_input("Target audience", value=brand.target_audience)

        brand.tone_of_voice = st.text_area(
            "Tone of voice",
            value=brand.tone_of_voice,
            height=90,
            help="Style cues (editorial, warm, considered, quiet confidence…).",
        )
        brand.brand_values = _split_lines(
            st.text_area(
                "Brand values (one per line)",
                value="\n".join(brand.brand_values),
                height=100,
            )
        )
        brand.signature_products = _split_lines(
            st.text_area(
                "Signature products (one per line)",
                value="\n".join(brand.signature_products),
                height=100,
            )
        )

        st.markdown("**Content pillars**")
        pillars_raw = st.text_area(
            "One pillar per line, format: Name | description | target share %",
            value="\n".join(
                f"{p.name} | {p.description} | {p.target_share_pct or ''}"
                for p in brand.content_pillars
            ),
            height=120,
            help="Example: `Origin stories | sourcing and tea makers | 25`",
        )
        pillars: list[ContentPillar] = []
        for line in pillars_raw.splitlines():
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split("|")]
            name = parts[0] if parts else ""
            desc = parts[1] if len(parts) > 1 else ""
            share_raw = parts[2] if len(parts) > 2 else ""
            share = int(share_raw) if share_raw.isdigit() else None
            pillars.append(ContentPillar(name=name, description=desc, target_share_pct=share))
        brand.content_pillars = pillars

        st.markdown("**Posting constraints**")
        c = brand.posting_constraints or PostingConstraint()
        cols = st.columns(2)
        c.max_posts_per_week = cols[0].number_input(
            "Max posts per week", min_value=1, max_value=21, value=c.max_posts_per_week
        )
        platforms_raw = cols[1].text_input(
            "Preferred platforms (comma separated)",
            value=", ".join(c.preferred_platforms),
        )
        c.preferred_platforms = [p.strip() for p in platforms_raw.split(",") if p.strip()]

        c.avoid_topics = _split_lines(
            st.text_area("Avoid topics (one per line)", value="\n".join(c.avoid_topics), height=80)
        )
        c.required_disclaimers = _split_lines(
            st.text_area(
                "Required disclaimers (one per line)",
                value="\n".join(c.required_disclaimers),
                height=60,
            )
        )
        brand.posting_constraints = c

        st.markdown("**Premium guardrails & forbidden hooks**")
        brand.premium_guardrails = _split_lines(
            st.text_area(
                "Premium guardrails (one per line)",
                value="\n".join(brand.premium_guardrails),
                height=100,
            )
        )
        brand.forbidden_hooks = _split_lines(
            st.text_area(
                "Forbidden hooks / phrases (one per line)",
                value="\n".join(brand.forbidden_hooks),
                height=80,
                help="Specific clichés or angles the brand has banned.",
            )
        )

        submitted = st.form_submit_button("Save brand profile", use_container_width=True)

    if submitted:
        saved = repo.save_brand(brand)
        st.success(f"Saved. Last updated {saved.updated_at.isoformat(timespec='seconds')}.")
