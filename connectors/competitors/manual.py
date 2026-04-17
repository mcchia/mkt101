"""Manual competitor record store.

No network access. All inputs are typed by the user and persisted locally.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, asdict
from typing import Any

from services import storage

_STORE = "competitors"


@dataclass
class Competitor:
    id: str
    name: str
    handles: list[str]
    urls: list[str]
    notes: str
    observations: list[dict[str, Any]]
    created_at: int


def _load() -> list[dict[str, Any]]:
    data = storage.load(_STORE, [])
    return data if isinstance(data, list) else []


def _save(items: list[dict[str, Any]]) -> None:
    storage.save(_STORE, items)


def list_competitors() -> list[Competitor]:
    out: list[Competitor] = []
    for raw in _load():
        try:
            out.append(
                Competitor(
                    id=str(raw["id"]),
                    name=str(raw.get("name", "")).strip(),
                    handles=[str(h).strip() for h in raw.get("handles", []) if str(h).strip()],
                    urls=[str(u).strip() for u in raw.get("urls", []) if str(u).strip()],
                    notes=str(raw.get("notes", "")),
                    observations=list(raw.get("observations", [])),
                    created_at=int(raw.get("created_at", 0)),
                )
            )
        except (KeyError, ValueError, TypeError):
            continue
    return out


def upsert(name: str, handles: list[str], urls: list[str], notes: str = "", competitor_id: str | None = None) -> Competitor:
    if not name.strip():
        raise ValueError("name is required")
    items = _load()
    if competitor_id:
        for raw in items:
            if raw.get("id") == competitor_id:
                raw["name"] = name.strip()
                raw["handles"] = [h.strip() for h in handles if h.strip()]
                raw["urls"] = [u.strip() for u in urls if u.strip()]
                raw["notes"] = notes.strip()
                _save(items)
                return Competitor(
                    id=raw["id"],
                    name=raw["name"],
                    handles=raw["handles"],
                    urls=raw["urls"],
                    notes=raw["notes"],
                    observations=list(raw.get("observations", [])),
                    created_at=int(raw.get("created_at", 0)),
                )
        raise KeyError(f"competitor not found: {competitor_id}")
    rec = Competitor(
        id=uuid.uuid4().hex[:12],
        name=name.strip(),
        handles=[h.strip() for h in handles if h.strip()],
        urls=[u.strip() for u in urls if u.strip()],
        notes=notes.strip(),
        observations=[],
        created_at=int(time.time()),
    )
    items.append(asdict(rec))
    _save(items)
    return rec


def delete(competitor_id: str) -> bool:
    items = _load()
    new = [r for r in items if r.get("id") != competitor_id]
    if len(new) == len(items):
        return False
    _save(new)
    return True


def add_observation(
    competitor_id: str,
    *,
    themes: list[str],
    frequency: str,
    offer_style: str,
    visual_patterns: str,
    campaign_angles: list[str],
    source: str,
    source_url: str = "",
) -> dict[str, Any]:
    items = _load()
    for raw in items:
        if raw.get("id") == competitor_id:
            obs = {
                "id": uuid.uuid4().hex[:10],
                "captured_at": int(time.time()),
                "themes": [t.strip() for t in themes if t.strip()],
                "frequency": frequency.strip(),
                "offer_style": offer_style.strip(),
                "visual_patterns": visual_patterns.strip(),
                "campaign_angles": [a.strip() for a in campaign_angles if a.strip()],
                "source": source.strip(),  # "manual" | "web"
                "source_url": source_url.strip(),
            }
            raw.setdefault("observations", []).append(obs)
            _save(items)
            return obs
    raise KeyError(f"competitor not found: {competitor_id}")
