"""Environment-driven configuration.

All external credentials and paths live here. Never hardcode secrets.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # Paths
    project_root: Path
    data_dir: Path
    log_dir: Path

    # LLM
    anthropic_api_key: str | None
    model: str
    max_output_tokens: int

    # Meta Graph API (all optional until user provides credentials)
    meta_access_token: str | None
    meta_fb_page_id: str | None
    meta_ig_user_id: str | None
    meta_graph_version: str

    # Crawler
    crawler_user_agent: str
    crawler_rate_limit_seconds: float
    crawler_max_pages: int
    crawler_request_timeout: int

    # Feature flags
    allow_autopost: bool

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    root = Path(os.environ.get("MKT101_ROOT", Path(__file__).resolve().parent.parent))
    data_dir = Path(os.environ.get("MKT101_DATA_DIR", root / "data"))
    log_dir = Path(os.environ.get("MKT101_LOG_DIR", root / "data" / "logs"))

    s = Settings(
        project_root=root,
        data_dir=data_dir,
        log_dir=log_dir,
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        model=os.environ.get("MKT101_MODEL", "claude-opus-4-7"),
        max_output_tokens=int(os.environ.get("MKT101_MAX_OUTPUT_TOKENS", "32000")),
        meta_access_token=os.environ.get("META_ACCESS_TOKEN"),
        meta_fb_page_id=os.environ.get("META_FB_PAGE_ID"),
        meta_ig_user_id=os.environ.get("META_IG_USER_ID"),
        meta_graph_version=os.environ.get("META_GRAPH_VERSION", "v21.0"),
        crawler_user_agent=os.environ.get(
            "CRAWLER_USER_AGENT",
            "mkt101-tea-brand-crawler/1.0 (+contact-your-team)",
        ),
        crawler_rate_limit_seconds=float(os.environ.get("CRAWLER_RATE_LIMIT_SECONDS", "1.0")),
        crawler_max_pages=int(os.environ.get("CRAWLER_MAX_PAGES", "80")),
        crawler_request_timeout=int(os.environ.get("CRAWLER_REQUEST_TIMEOUT", "15")),
        allow_autopost=_env_bool("ALLOW_AUTOPOST", False),
    )
    s.ensure_dirs()
    return s
