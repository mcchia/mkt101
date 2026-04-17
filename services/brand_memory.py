"""Persistent brand memory layer.

Stores the editable truth about the brand (tone, audience, pillars, guardrails,
banned phrases, CTA style, positioning notes, posting constraints) separately
from assistant-inferred recommendations. The main assistant, idea generation,
critique, top-3 selection, and execution briefs all consume the editable copy.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from . import storage

_STORE = "brand_memory"

# Brand memory lives under two keys so the UI can show editable truth vs
# inferred recommendations side-by-side.
_EDITABLE_KEY = "editable"
_INFERRED_KEY = "inferred"


@dataclass
class BrandMemory:
    tone_of_voice: str = ""
    target_audience: str = ""
    content_pillars: list[str] = field(default_factory=list)
    premium_guardrails: list[str] = field(default_factory=list)
    banned_phrases: list[str] = field(default_factory=list)
    preferred_cta_style: str = ""
    positioning_notes: str = ""
    posting_constraints: str = ""

    def is_empty(self) -> bool:
        return not any(
            [
                self.tone_of_voice.strip(),
                self.target_audience.strip(),
                self.content_pillars,
                self.premium_guardrails,
                self.banned_phrases,
                self.preferred_cta_style.strip(),
                self.positioning_notes.strip(),
                self.posting_constraints.strip(),
            ]
        )


def _default_doc() -> dict[str, Any]:
    return {_EDITABLE_KEY: asdict(BrandMemory()), _INFERRED_KEY: asdict(BrandMemory())}


def _load_doc() -> dict[str, Any]:
    doc = storage.load(_STORE, _default_doc())
    if not isinstance(doc, dict):
        return _default_doc()
    # Repair partial documents defensively.
    doc.setdefault(_EDITABLE_KEY, asdict(BrandMemory()))
    doc.setdefault(_INFERRED_KEY, asdict(BrandMemory()))
    return doc


def _coerce(raw: dict[str, Any]) -> BrandMemory:
    mem = BrandMemory()
    for k in asdict(mem).keys():
        v = raw.get(k, getattr(mem, k))
        if isinstance(getattr(mem, k), list):
            if isinstance(v, list):
                setattr(mem, k, [str(x).strip() for x in v if str(x).strip()])
            elif isinstance(v, str):
                setattr(
                    mem,
                    k,
                    [line.strip() for line in v.splitlines() if line.strip()],
                )
        else:
            setattr(mem, k, str(v or "").strip())
    return mem


def load_editable() -> BrandMemory:
    return _coerce(_load_doc()[_EDITABLE_KEY])


def load_inferred() -> BrandMemory:
    return _coerce(_load_doc()[_INFERRED_KEY])


def save_editable(mem: BrandMemory) -> None:
    doc = _load_doc()
    doc[_EDITABLE_KEY] = asdict(mem)
    storage.save(_STORE, doc)


def save_inferred(mem: BrandMemory) -> None:
    doc = _load_doc()
    doc[_INFERRED_KEY] = asdict(mem)
    storage.save(_STORE, doc)


def system_block() -> str:
    """Return a safe-to-prepend system string built from editable memory.

    Empty sections are omitted to keep the prompt tight. If the whole memory is
    empty the function returns an empty string so callers can skip the block.
    """
    mem = load_editable()
    if mem.is_empty():
        return ""

    lines: list[str] = ["## Brand memory (authoritative, set by the team)"]

    def _kv(label: str, value: str) -> None:
        v = value.strip()
        if v:
            lines.append(f"- {label}: {v}")

    def _list(label: str, values: list[str]) -> None:
        vs = [v for v in values if v.strip()]
        if vs:
            lines.append(f"- {label}:")
            for v in vs:
                lines.append(f"  * {v.strip()}")

    _kv("Tone of voice", mem.tone_of_voice)
    _kv("Target audience", mem.target_audience)
    _list("Content pillars", mem.content_pillars)
    _list("Premium guardrails (must respect)", mem.premium_guardrails)
    _list("Banned phrases (must not use)", mem.banned_phrases)
    _kv("Preferred CTA style", mem.preferred_cta_style)
    _kv("Positioning notes", mem.positioning_notes)
    _kv("Posting constraints", mem.posting_constraints)

    lines.append(
        "\nTreat this memory as authoritative. If a request conflicts with it, "
        "flag the conflict and defer to brand memory unless the user explicitly "
        "overrides."
    )
    return "\n".join(lines)
