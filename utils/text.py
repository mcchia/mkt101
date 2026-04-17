"""Text cleaning and parsing helpers."""
from __future__ import annotations

import re
from typing import Iterable


_WS_RE = re.compile(r"\s+")
_MULTIPLE_NL = re.compile(r"\n{3,}")


def clean_whitespace(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ").replace("\u200b", "")
    text = _WS_RE.sub(" ", text)
    return text.strip()


def normalize_paragraphs(text: str) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines()]
    joined = "\n".join(lines)
    return _MULTIPLE_NL.sub("\n\n", joined).strip()


def parse_price(raw: str | None) -> float | None:
    if not raw:
        return None
    cleaned = re.sub(r"[^\d.,]", "", raw).replace(",", "")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def dedupe_preserve(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"
