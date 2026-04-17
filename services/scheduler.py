"""Lightweight scheduler for daily ingestion syncs.

Streamlit reruns are request-driven, so we don't try to run a real background
daemon from inside the app (it would be unreliable and a vector for leaks).
Instead:

1. The user sets an enable flag, a time-of-day, and which sources to sync.
2. On each Streamlit rerun, `check_and_run()` sees if a run is due and, if so,
   the UI exposes a "Run now" button; it does NOT auto-execute in the request
   thread by default, which keeps UI latency predictable.
3. A standalone runner `scripts/run_sync.py` can be invoked via cron or a
   systemd timer for true hands-off daily syncs. It updates the same state.

Sync history is kept short (last 20 runs) and does not store prompts, payloads,
credentials, or URLs with query strings. Only run metadata and a safe summary.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable

from . import storage

_STORE_CONFIG = "scheduler_config"
_STORE_HISTORY = "scheduler_history"

SOURCE_CHOICES = ["content_history_refresh", "competitor_web_refresh", "pattern_recompute"]


@dataclass
class ScheduleConfig:
    enabled: bool = False
    time_of_day: str = "08:00"  # HH:MM local
    sources: list[str] | None = None

    def normalized_sources(self) -> list[str]:
        if not self.sources:
            return []
        return [s for s in self.sources if s in SOURCE_CHOICES]


def _default_config() -> dict[str, Any]:
    return {"enabled": False, "time_of_day": "08:00", "sources": []}


def load_config() -> ScheduleConfig:
    raw = storage.load(_STORE_CONFIG, _default_config())
    if not isinstance(raw, dict):
        raw = _default_config()
    return ScheduleConfig(
        enabled=bool(raw.get("enabled", False)),
        time_of_day=str(raw.get("time_of_day", "08:00")),
        sources=list(raw.get("sources", [])),
    )


def save_config(cfg: ScheduleConfig) -> None:
    # Validate time format.
    try:
        datetime.strptime(cfg.time_of_day, "%H:%M")
    except ValueError:
        raise ValueError("time_of_day must be HH:MM")
    storage.save(
        _STORE_CONFIG,
        {
            "enabled": bool(cfg.enabled),
            "time_of_day": cfg.time_of_day,
            "sources": cfg.normalized_sources(),
        },
    )


def load_history() -> list[dict[str, Any]]:
    data = storage.load(_STORE_HISTORY, [])
    return data if isinstance(data, list) else []


def _append_history(entry: dict[str, Any]) -> None:
    items = load_history()
    items.append(entry)
    # Keep only last 20.
    items = items[-20:]
    storage.save(_STORE_HISTORY, items)


def next_run_at(cfg: ScheduleConfig, now: datetime | None = None) -> datetime | None:
    if not cfg.enabled:
        return None
    now = now or datetime.now()
    try:
        hh, mm = [int(p) for p in cfg.time_of_day.split(":")]
    except (ValueError, IndexError):
        return None
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if target <= now:
        target = target + timedelta(days=1)
    # If we already ran today after the scheduled time, target is tomorrow.
    last = last_successful_run_time()
    if last is not None:
        today_target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if last >= today_target and today_target <= now:
            target = today_target + timedelta(days=1)
    return target


def last_successful_run_time() -> datetime | None:
    for entry in reversed(load_history()):
        if entry.get("status") == "ok":
            ts = entry.get("finished_at")
            if isinstance(ts, (int, float)):
                return datetime.fromtimestamp(ts)
    return None


def is_due(cfg: ScheduleConfig, now: datetime | None = None) -> bool:
    if not cfg.enabled:
        return False
    now = now or datetime.now()
    try:
        hh, mm = [int(p) for p in cfg.time_of_day.split(":")]
    except (ValueError, IndexError):
        return False
    today_target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if now < today_target:
        return False
    last = last_successful_run_time()
    if last is None:
        return True
    return last < today_target


# ---- Sync handlers ----------------------------------------------------------


def _handler_content_history_refresh() -> str:
    """Recompute fatigue view. Safe, local, no network."""
    from . import content_history

    rep = content_history.analyze_fatigue(lookback=20)
    return f"history: {len(content_history.list_records())} records; {len(rep.warnings)} fatigue warnings"


def _handler_pattern_recompute() -> str:
    from . import losing_posts, patterns

    top = patterns.extract(metric="weighted", top_n=5)
    losing = losing_posts.extract(metric="weighted", bottom_n=5)
    return (
        f"patterns: n={top.sample_size} strong={len(top.strong)}; "
        f"losing: rows={len(losing.rows)}"
    )


def _handler_competitor_web_refresh() -> str:
    """Fetch the first URL of each competitor (one per competitor per run)."""
    from connectors.competitors import manual, web as web_mod
    from . import competitor_watch

    comps = manual.list_competitors()
    ok = 0
    errors = 0
    for c in comps:
        for url in c.urls:
            try:
                competitor_watch.capture_web_observation(c.id, url)
                ok += 1
                break
            except Exception:
                errors += 1
                continue
    return f"competitors: ok={ok} errors={errors}"


_HANDLERS: dict[str, Callable[[], str]] = {
    "content_history_refresh": _handler_content_history_refresh,
    "pattern_recompute": _handler_pattern_recompute,
    "competitor_web_refresh": _handler_competitor_web_refresh,
}


def run_sync_now(sources: list[str] | None = None) -> dict[str, Any]:
    """Execute the configured (or given) sources once and append to history.

    Never raises: all per-source errors are captured and summarized. Returns the
    history entry.
    """
    cfg = load_config()
    to_run = [s for s in (sources or cfg.normalized_sources()) if s in _HANDLERS]
    started = time.time()
    per_source: list[dict[str, Any]] = []
    overall_ok = True
    for source in to_run:
        handler = _HANDLERS[source]
        s_start = time.time()
        try:
            summary = handler()
            per_source.append(
                {
                    "source": source,
                    "status": "ok",
                    "summary": str(summary)[:200],
                    "duration_ms": int((time.time() - s_start) * 1000),
                }
            )
        except Exception as exc:
            overall_ok = False
            # Store a generic message. Never embed stack traces or URLs.
            per_source.append(
                {
                    "source": source,
                    "status": "error",
                    "summary": f"{type(exc).__name__} occurred",
                    "duration_ms": int((time.time() - s_start) * 1000),
                }
            )
    finished = time.time()
    entry = {
        "started_at": started,
        "finished_at": finished,
        "status": "ok" if overall_ok and to_run else ("noop" if not to_run else "error"),
        "sources": to_run,
        "per_source": per_source,
    }
    _append_history(entry)
    return entry
