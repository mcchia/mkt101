"""Structured logging helpers.

Writes JSON lines to data/logs/app.jsonl for auditability and also mirrors
to stderr for the terminal. Keep it simple; one file, append-only.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import get_settings


class JsonLinesHandler(logging.Handler):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, record: logging.LogRecord) -> None:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.format(record)
        extras = getattr(record, "extras", None)
        if isinstance(extras, dict):
            payload["extras"] = extras
        try:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, default=str) + "\n")
        except Exception:
            pass


_configured = False


def get_logger(name: str = "mkt101") -> logging.Logger:
    global _configured
    logger = logging.getLogger(name)
    if not _configured:
        logger.setLevel(logging.INFO)
        settings = get_settings()
        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        logger.addHandler(stream)
        logger.addHandler(JsonLinesHandler(settings.log_dir / "app.jsonl"))
        logger.propagate = False
        _configured = True
    return logger


def log_event(name: str, **extras: Any) -> None:
    """Emit a structured event line."""
    logger = get_logger()
    logger.info(name, extra={"extras": extras})
