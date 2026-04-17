"""Premium brand protection checker.

Transparent, rule-based triage plus an optional LLM review pass. Every flag
carries a category, a severity, the offending excerpt, and a human-readable
reason. No black-box good/bad scores.
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any

from . import brand_memory, storage
from .llm import run_json

_STORE = "brand_protection_flags"

# Heuristic rule catalogue. Each rule is a tuple of (category, severity, regex, reason).
# Severities: "low", "medium", "high".
_RULES: list[tuple[str, str, re.Pattern, str]] = [
    (
        "discount_heavy",
        "high",
        re.compile(r"\b(\d{1,2}|\d{2,3})\s?%\s?off\b", re.IGNORECASE),
        "Heavy discount framing reads as mass-market and erodes premium perception.",
    ),
    (
        "clickbait",
        "medium",
        re.compile(r"\b(you won'?t believe|must see|shocking|crazy deal|insane)\b", re.IGNORECASE),
        "Clickbait phrasing is inconsistent with a middle-to-high-end tea brand.",
    ),
    (
        "urgency_pressure",
        "medium",
        re.compile(r"\b(hurry|last chance|don'?t miss out|buy now|act fast|limited time only)\b", re.IGNORECASE),
        "High-pressure urgency cues feel cheap and noisy for a premium audience.",
    ),
    (
        "superlative_spam",
        "low",
        re.compile(r"\b(best ever|#1|the best tea in the world|unbeatable|world'?s best)\b", re.IGNORECASE),
        "Unqualified superlatives look promotional and undermine credibility.",
    ),
    (
        "low_trust_claim",
        "medium",
        re.compile(r"\b(miracle|detox|cure|heal|burn fat|instant results)\b", re.IGNORECASE),
        "Wellness overclaims create trust risk and can conflict with ad policies.",
    ),
    (
        "emoji_spam",
        "low",
        re.compile(r"(?:[\U0001F300-\U0001FAFF\u2600-\u27BF]\s?){5,}"),
        "Emoji spam reads as noisy and mass-market.",
    ),
    (
        "all_caps_shout",
        "low",
        re.compile(r"\b[A-Z]{6,}\b"),
        "ALL-CAPS shouting is inconsistent with a calm premium voice.",
    ),
    (
        "cheap_price_lead",
        "medium",
        re.compile(r"\b(cheap|cheapest|bargain|lowest price|price drop)\b", re.IGNORECASE),
        "Leading with cheapness contradicts premium positioning.",
    ),
    (
        "trend_misfit",
        "low",
        re.compile(r"\b(no cap|slay|rizz|gyatt|bussin'?|skibidi)\b", re.IGNORECASE),
        "Meme/trend slang can clash with a premium audience if used carelessly.",
    ),
]


@dataclass
class Flag:
    category: str
    severity: str  # low | medium | high
    excerpt: str
    reason: str
    source: str  # "rule" | "llm" | "brand_memory"


@dataclass
class ProtectionReport:
    score: int  # 0 (clean) to 100 (severe)
    summary: str
    flags: list[Flag]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "summary": self.summary,
            "flags": [asdict(f) for f in self.flags],
        }


def _rule_flags(text: str) -> list[Flag]:
    out: list[Flag] = []
    for category, severity, rx, reason in _RULES:
        for m in rx.finditer(text):
            out.append(
                Flag(
                    category=category,
                    severity=severity,
                    excerpt=m.group(0),
                    reason=reason,
                    source="rule",
                )
            )
    return out


def _banned_phrase_flags(text: str) -> list[Flag]:
    mem = brand_memory.load_editable()
    out: list[Flag] = []
    for phrase in mem.banned_phrases:
        p = phrase.strip()
        if not p:
            continue
        if re.search(re.escape(p), text, re.IGNORECASE):
            out.append(
                Flag(
                    category="banned_phrase",
                    severity="high",
                    excerpt=p,
                    reason="Phrase is on the brand-memory banned list.",
                    source="brand_memory",
                )
            )
    return out


def _score(flags: list[Flag]) -> int:
    weights = {"low": 5, "medium": 12, "high": 25}
    raw = sum(weights.get(f.severity, 0) for f in flags)
    return min(100, raw)


def _summary(flags: list[Flag], score: int) -> str:
    if not flags:
        return "No premium-brand risks detected."
    parts: list[str] = []
    by_cat: dict[str, int] = {}
    for f in flags:
        by_cat[f.category] = by_cat.get(f.category, 0) + 1
    for cat, n in by_cat.items():
        parts.append(f"{cat} x{n}")
    level = "low" if score < 20 else "medium" if score < 50 else "high"
    return f"Risk level: {level} ({score}/100). " + "; ".join(parts)


_LLM_EXTRA = """## Premium brand protection review

You will review a text draft (hook, caption, CTA, or idea description) against
premium positioning for a middle-to-high-end tea brand. Respond with JSON only.

Only flag genuine concerns. If the text is clean, return an empty flags list.

Each flag must include:
- category: one of ["cheap_tone", "overly_promotional", "noisy", "wrong_trend",
  "mass_market", "premium_inconsistency", "trust_risk"]
- severity: "low" | "medium" | "high"
- excerpt: the exact offending substring
- reason: why it undermines the premium brand

Schema:
{ "flags": [ {"category": "...", "severity": "...", "excerpt": "...", "reason": "..."} ] }
"""


def check(text: str, use_llm: bool = True) -> ProtectionReport:
    """Run the full check. `use_llm=False` keeps it offline (rules only)."""
    if not text or not text.strip():
        return ProtectionReport(score=0, summary="Empty input.", flags=[])

    flags: list[Flag] = []
    flags.extend(_rule_flags(text))
    flags.extend(_banned_phrase_flags(text))

    if use_llm:
        try:
            raw = run_json(
                f"Text to review:\n---\n{text.strip()}\n---\nReturn JSON as specified.",
                extra_system=_LLM_EXTRA,
                max_tokens=2000,
            )
            items = raw.get("flags", []) if isinstance(raw, dict) else []
            for item in items:
                if not isinstance(item, dict):
                    continue
                flags.append(
                    Flag(
                        category=str(item.get("category", "premium_inconsistency")),
                        severity=str(item.get("severity", "low")),
                        excerpt=str(item.get("excerpt", ""))[:200],
                        reason=str(item.get("reason", "")),
                        source="llm",
                    )
                )
        except Exception:
            # Rule-only fallback; don't let API issues block the user.
            pass

    score = _score(flags)
    return ProtectionReport(score=score, summary=_summary(flags, score), flags=flags)


# -------- Flag log (optional persistence) ------------------------------------


def _load_log() -> list[dict[str, Any]]:
    data = storage.load(_STORE, [])
    return data if isinstance(data, list) else []


def log_report(label: str, text: str, report: ProtectionReport) -> dict[str, Any]:
    entry = {
        "id": uuid.uuid4().hex[:12],
        "created_at": int(time.time()),
        "label": label.strip(),
        "text_snippet": text[:500],
        "report": report.to_dict(),
    }
    items = _load_log()
    items.append(entry)
    storage.save(_STORE, items)
    return entry


def list_logged() -> list[dict[str, Any]]:
    return _load_log()
