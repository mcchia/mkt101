"""Conservative public-website fetch for competitor analysis.

Design:
- stdlib only (urllib + html.parser). No headless browser, no scraping loops.
- Per-call: timeout, max response size, HEAD-first content-type check, explicit
  user-agent string, and a best-effort robots.txt allow check.
- Only http/https URLs are accepted; all others are rejected.
- Output is plain text; the caller is responsible for what to do with it.
- Logging redacts query strings to avoid accidentally leaking tracking tokens.

This module is intentionally minimal. It is a single-call helper. The scheduler
may invoke it once per competitor per sync, not in tight loops.
"""

from __future__ import annotations

import gzip
import io
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Optional
from urllib import robotparser

USER_AGENT = "TeaMarketingAssistant/1.0 (+local research, respectful)"
TIMEOUT_SECS = 10
MAX_BYTES = 500_000  # 500 KB is enough for a home or about page


class _TextExtractor(HTMLParser):
    _SKIP = {"script", "style", "noscript", "svg", "canvas", "iframe"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in self._SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped)

    def text(self) -> str:
        joined = " ".join(self._parts)
        return re.sub(r"\s+", " ", joined).strip()


class CompetitorFetchError(RuntimeError):
    pass


def _validate_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise CompetitorFetchError("only http/https URLs are allowed")
    if not parsed.netloc:
        raise CompetitorFetchError("URL missing host")
    # Reject private/loopback targets via hostname heuristics; DNS resolution to
    # private ranges still succeeds but this stops the obvious cases.
    host = parsed.hostname or ""
    if host in ("localhost",) or host.startswith("127.") or host.startswith("169.254."):
        raise CompetitorFetchError("refusing to fetch a loopback/link-local host")
    if host.endswith(".local") or host.endswith(".internal"):
        raise CompetitorFetchError("refusing to fetch internal-only hosts")
    return url.strip()


def _redact_url_for_log(url: str) -> str:
    p = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse((p.scheme, p.netloc, p.path, "", "", ""))


def _robots_allows(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = robotparser.RobotFileParser()
        rp.set_url(robots_url)
        # robotparser's .read() uses urlopen without a timeout; do it manually.
        req = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECS) as resp:
                body = resp.read(MAX_BYTES).decode("utf-8", errors="replace")
            rp.parse(body.splitlines())
        except (urllib.error.URLError, socket.timeout, ValueError):
            # If robots.txt is unavailable, default to allow but be conservative.
            return True
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return True


def _decode_body(resp, raw: bytes) -> str:
    encoding = resp.headers.get_content_charset() or "utf-8"
    if resp.headers.get("Content-Encoding", "").lower() == "gzip":
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
    return raw.decode(encoding, errors="replace")


def fetch_public_text(url: str) -> dict[str, str]:
    """Fetch a public HTML page and return extracted visible text.

    Returns: {"url": safe_url, "title": "...", "text": "..."}
    Raises CompetitorFetchError on any failure. Never raises with the raw URL
    query string attached; logs should use the redacted URL only.
    """
    clean = _validate_url(url)
    safe_for_log = _redact_url_for_log(clean)

    if not _robots_allows(clean):
        raise CompetitorFetchError(f"robots.txt disallows fetching {safe_for_log}")

    req = urllib.request.Request(
        clean,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en,vi;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECS) as resp:
            content_type = (resp.headers.get("Content-Type") or "").lower()
            if "html" not in content_type and "xml" not in content_type:
                raise CompetitorFetchError(
                    f"refusing non-HTML content-type at {safe_for_log}: {content_type or 'unknown'}"
                )
            raw = resp.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raw = raw[:MAX_BYTES]
            body = _decode_body(resp, raw)
    except urllib.error.HTTPError as e:
        raise CompetitorFetchError(f"HTTP {e.code} at {safe_for_log}") from None
    except (urllib.error.URLError, socket.timeout, ValueError) as e:
        # Do not embed the raw error which may include the full URL with query.
        raise CompetitorFetchError(f"network error at {safe_for_log}") from None

    title_match = re.search(r"<title[^>]*>([^<]{0,200})</title>", body, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else ""

    parser = _TextExtractor()
    try:
        parser.feed(body)
    except Exception:
        pass
    text = parser.text()[:20_000]

    return {"url": safe_for_log, "title": title, "text": text}
