"""Lightweight JSON-file repository.

Each entity type lives in one JSON file under data/. Reads and writes are
whole-file; fine for the expected volume of a single brand's marketing data.
Simpler to inspect than SQLite and easy to migrate later if needed.
"""
from __future__ import annotations

import json
import tempfile
import threading
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional, Type, TypeVar

from pydantic import BaseModel

from config import get_settings
from models import (
    BrandProfile,
    CalendarEntry,
    ContentIdea,
    DecisionLogEntry,
    Post,
    SourceRecord,
    SyncRun,
)

T = TypeVar("T", bound=BaseModel)


def _default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "value"):
        return obj.value
    raise TypeError(f"Not serializable: {type(obj)}")


class Repository:
    """A tiny multi-collection JSON store."""

    FILES = {
        "brand": "brand.json",
        "posts": "posts.json",
        "ideas": "ideas.json",
        "calendar": "calendar.json",
        "syncs": "syncs.json",
        "sources": "sources.json",
        "decisions": "decisions.json",
    }

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    # ---------- low level ----------

    def _path(self, key: str) -> Path:
        return self.data_dir / self.FILES[key]

    def _read(self, key: str) -> Any:
        path = self._path(key)
        if not path.exists():
            return None if key == "brand" else []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None if key == "brand" else []

    def _write(self, key: str, data: Any) -> None:
        path = self._path(key)
        with self._lock:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=path.parent,
                delete=False,
                prefix=f".{path.name}.",
                suffix=".tmp",
            ) as tmp:
                json.dump(data, tmp, indent=2, default=_default, ensure_ascii=False)
                tmp_path = Path(tmp.name)
            tmp_path.replace(path)

    def _load_list(self, key: str, model: Type[T]) -> list[T]:
        raw = self._read(key) or []
        return [model.model_validate(row) for row in raw]

    def _save_list(self, key: str, items: Iterable[BaseModel]) -> None:
        self._write(key, [i.model_dump(mode="json") for i in items])

    # ---------- brand ----------

    def get_brand(self) -> Optional[BrandProfile]:
        raw = self._read("brand")
        if not raw:
            return None
        return BrandProfile.model_validate(raw)

    def save_brand(self, brand: BrandProfile) -> BrandProfile:
        brand.touch()
        self._write("brand", brand.model_dump(mode="json"))
        return brand

    # ---------- posts ----------

    def list_posts(self) -> list[Post]:
        return self._load_list("posts", Post)

    def upsert_posts(self, posts: Iterable[Post]) -> int:
        existing = {p.id: p for p in self.list_posts()}
        added = 0
        for p in posts:
            if p.id not in existing:
                added += 1
            existing[p.id] = p
        self._save_list("posts", existing.values())
        return added

    def replace_posts(self, posts: Iterable[Post]) -> None:
        self._save_list("posts", posts)

    def clear_posts(self) -> None:
        self._save_list("posts", [])

    # ---------- ideas ----------

    def list_ideas(self) -> list[ContentIdea]:
        return self._load_list("ideas", ContentIdea)

    def add_ideas(self, ideas: Iterable[ContentIdea]) -> None:
        current = self.list_ideas()
        current.extend(ideas)
        self._save_list("ideas", current)

    def save_idea(self, idea: ContentIdea) -> None:
        items = self.list_ideas()
        idea.touch()
        for i, existing in enumerate(items):
            if existing.id == idea.id:
                items[i] = idea
                break
        else:
            items.append(idea)
        self._save_list("ideas", items)

    def delete_idea(self, idea_id: str) -> None:
        items = [i for i in self.list_ideas() if i.id != idea_id]
        self._save_list("ideas", items)

    def get_idea(self, idea_id: str) -> Optional[ContentIdea]:
        for idea in self.list_ideas():
            if idea.id == idea_id:
                return idea
        return None

    # ---------- calendar ----------

    def list_calendar(self) -> list[CalendarEntry]:
        return self._load_list("calendar", CalendarEntry)

    def save_calendar_entry(self, entry: CalendarEntry) -> None:
        items = self.list_calendar()
        entry.updated_at = datetime.now(timezone.utc)
        for i, existing in enumerate(items):
            if existing.id == entry.id:
                items[i] = entry
                break
        else:
            items.append(entry)
        self._save_list("calendar", items)

    def delete_calendar_entry(self, entry_id: str) -> None:
        items = [i for i in self.list_calendar() if i.id != entry_id]
        self._save_list("calendar", items)

    # ---------- syncs ----------

    def list_syncs(self) -> list[SyncRun]:
        return self._load_list("syncs", SyncRun)

    def save_sync(self, run: SyncRun) -> None:
        items = self.list_syncs()
        for i, existing in enumerate(items):
            if existing.id == run.id:
                items[i] = run
                break
        else:
            items.append(run)
        self._save_list("syncs", items)

    # ---------- sources ----------

    def list_sources(self) -> list[SourceRecord]:
        return self._load_list("sources", SourceRecord)

    def add_sources(self, records: Iterable[SourceRecord]) -> int:
        existing = self.list_sources()
        seen_urls = {r.url for r in existing if r.url}
        added = 0
        for r in records:
            if r.url and r.url in seen_urls:
                continue
            existing.append(r)
            if r.url:
                seen_urls.add(r.url)
            added += 1
        self._save_list("sources", existing)
        return added

    def clear_sources(self, source_run_id: str | None = None) -> None:
        if source_run_id is None:
            self._save_list("sources", [])
            return
        kept = [r for r in self.list_sources() if r.source_run_id != source_run_id]
        self._save_list("sources", kept)

    # ---------- decisions ----------

    def list_decisions(self) -> list[DecisionLogEntry]:
        return self._load_list("decisions", DecisionLogEntry)

    def add_decision(self, entry: DecisionLogEntry) -> None:
        items = self.list_decisions()
        items.append(entry)
        self._save_list("decisions", items)


@lru_cache(maxsize=1)
def get_repository() -> Repository:
    settings = get_settings()
    return Repository(settings.data_dir)
