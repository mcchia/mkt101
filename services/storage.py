"""Tiny JSON-file persistence layer.

Design goals:
- No new dependencies.
- Atomic writes (temp file + os.replace) so a crash never leaves half-written data.
- Path traversal safe: caller passes a short logical name, we resolve within DATA_DIR.
- Never stores secrets. Caller is responsible for keeping credentials out of payloads.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from pathlib import Path
from typing import Any

DATA_DIR = Path(os.environ.get("TEA_DATA_DIR", "data")).resolve()

_NAME_RE = re.compile(r"^[a-z0-9_\-]+$")
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(name: str) -> threading.Lock:
    with _locks_guard:
        lock = _locks.get(name)
        if lock is None:
            lock = threading.Lock()
            _locks[name] = lock
        return lock


def _path_for(name: str) -> Path:
    if not _NAME_RE.match(name):
        raise ValueError(f"invalid storage name: {name!r}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"{name}.json"


def load(name: str, default: Any) -> Any:
    """Load JSON at name, or return default if file is missing/unreadable."""
    path = _path_for(name)
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save(name: str, value: Any) -> None:
    """Atomically write JSON to name."""
    path = _path_for(name)
    with _lock_for(name):
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=f".{name}.", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(value, f, ensure_ascii=False, indent=2, sort_keys=False)
            os.replace(tmp, path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
