"""Standalone daily sync runner.

Intended for cron or a systemd timer. Example crontab entry:

    0 8 * * *  cd /path/to/mkt101 && /path/to/venv/bin/python -m scripts.run_sync

Loads secrets the same way the app does (env / .env / Streamlit secrets),
runs the configured scheduler sources, prints a one-line summary to stdout,
and returns a non-zero exit code on per-source errors. Does NOT print the
API key, competitor URLs with query strings, or any prompt content.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make the project root importable when executed as `python scripts/run_sync.py`.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services import scheduler  # noqa: E402


def main() -> int:
    entry = scheduler.run_sync_now()
    safe = {
        "status": entry["status"],
        "sources": entry["sources"],
        "per_source": entry["per_source"],
    }
    print(json.dumps(safe, ensure_ascii=False))
    return 0 if entry["status"] in ("ok", "noop") else 1


if __name__ == "__main__":
    raise SystemExit(main())
