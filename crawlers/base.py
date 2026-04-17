"""Shared crawler types and a polite-fetch helper."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from urllib.robotparser import RobotFileParser

import requests

from config import get_settings
from utils.logging import log_event


@dataclass
class CrawlConfig:
    start_url: str
    max_pages: int = 60
    rate_limit_seconds: float = 1.0
    same_domain_only: bool = True
    respect_robots: bool = True
    user_agent: str | None = None
    request_timeout: int = 15


@dataclass
class CrawlResult:
    fetched_urls: list[str] = field(default_factory=list)
    pages: list[dict] = field(default_factory=list)  # structured per-page dicts
    errors: list[str] = field(default_factory=list)
    robots_blocked: list[str] = field(default_factory=list)


class PoliteFetcher:
    """Simple rate-limited, robots-aware GET fetcher."""

    def __init__(self, config: CrawlConfig) -> None:
        s = get_settings()
        self.config = config
        self.user_agent = config.user_agent or s.crawler_user_agent
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self.user_agent})
        self._last_fetch: float = 0.0
        self._robots: RobotFileParser | None = None

    def _load_robots(self, root: str) -> None:
        if not self.config.respect_robots:
            return
        rp = RobotFileParser()
        rp.set_url(root.rstrip("/") + "/robots.txt")
        try:
            rp.read()
            self._robots = rp
        except Exception:
            self._robots = None

    def can_fetch(self, url: str) -> bool:
        if not self.config.respect_robots or not self._robots:
            return True
        try:
            return self._robots.can_fetch(self.user_agent, url)
        except Exception:
            return True

    def get(self, url: str) -> requests.Response | None:
        # Rate limit between hits
        wait = self.config.rate_limit_seconds - (time.time() - self._last_fetch)
        if wait > 0:
            time.sleep(wait)
        try:
            resp = self._session.get(url, timeout=self.config.request_timeout)
        except requests.RequestException as e:
            log_event("crawler_fetch_error", url=url, error=str(e))
            return None
        finally:
            self._last_fetch = time.time()
        if resp.status_code >= 400:
            log_event("crawler_http_error", url=url, status=resp.status_code)
            return None
        return resp

    def ensure_robots(self, root: str) -> None:
        if self._robots is None:
            self._load_robots(root)
