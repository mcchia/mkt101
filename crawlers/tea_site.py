"""Tea brand website crawler.

Goals: give the assistant a structured view of the brand's products, pillars,
and messaging, so downstream ideas are grounded in reality. Uses requests +
BeautifulSoup only — no Playwright. Respects robots.txt and rate limits.
"""
from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from crawlers.base import CrawlConfig, CrawlResult, PoliteFetcher
from utils.logging import log_event
from utils.text import clean_whitespace, dedupe_preserve, parse_price, truncate


_CATEGORY_HINTS = [
    "black tea", "green tea", "oolong", "pu'er", "pu-erh", "puer", "white tea",
    "matcha", "herbal", "tisane", "rooibos", "chai", "yellow tea",
]

_GIFT_PATTERNS = re.compile(r"\b(gift(\s+set)?|bundle|hamper)\b", re.IGNORECASE)
_PRICE_HINT_RE = re.compile(r"(\$|USD|€|£|¥|SGD|AUD|HKD|RMB|元)\s?\d")


@dataclass
class _PageExtract:
    url: str
    page_type: str
    title: str
    product_name: str | None
    product_category: str | None
    price: float | None
    description: str
    tasting_notes: list[str]
    ingredients: list[str]
    is_gift_set: bool
    cta_text: list[str]
    hero_headline: str | None
    featured_collections: list[str]
    brand_snippets: list[str]

    def to_dict(self) -> dict:
        return {
            "page_url": self.url,
            "page_type": self.page_type,
            "title": self.title,
            "product_name": self.product_name,
            "product_category": self.product_category,
            "price": self.price,
            "description": self.description,
            "tasting_notes": self.tasting_notes,
            "ingredients": self.ingredients,
            "is_gift_set": self.is_gift_set,
            "cta_text": self.cta_text,
            "hero_headline": self.hero_headline,
            "featured_collections": self.featured_collections,
            "brand_snippets": self.brand_snippets,
        }


class TeaSiteCrawler:
    """BFS crawler with shallow, brand-focused extraction."""

    def __init__(self, config: CrawlConfig) -> None:
        self.config = config
        self.fetcher = PoliteFetcher(config)

    def crawl(self, on_progress: Callable[[int, int, str], None] | None = None) -> CrawlResult:
        result = CrawlResult()
        start = self.config.start_url
        if not start.startswith("http"):
            start = "https://" + start

        parsed_start = urlparse(start)
        root = f"{parsed_start.scheme}://{parsed_start.netloc}"
        self.fetcher.ensure_robots(root)

        queue: deque[str] = deque([start])
        seen: set[str] = {start}

        while queue and len(result.pages) < self.config.max_pages:
            url = queue.popleft()
            if not self.fetcher.can_fetch(url):
                result.robots_blocked.append(url)
                continue
            resp = self.fetcher.get(url)
            if resp is None:
                result.errors.append(f"Fetch failed: {url}")
                continue
            result.fetched_urls.append(url)

            soup = BeautifulSoup(resp.text, "html.parser")
            extract = self._extract(url, soup)
            if extract:
                result.pages.append(extract.to_dict())
                if on_progress:
                    on_progress(len(result.pages), self.config.max_pages, url)

            # Enqueue same-domain links up to the cap
            for link in self._extract_links(url, soup, parsed_start.netloc):
                if link not in seen and len(seen) < self.config.max_pages * 3:
                    seen.add(link)
                    queue.append(link)

        log_event(
            "crawl_complete",
            start=start,
            fetched=len(result.fetched_urls),
            pages=len(result.pages),
            errors=len(result.errors),
            robots_blocked=len(result.robots_blocked),
        )
        return result

    # ---------- link discovery ----------

    def _extract_links(self, base_url: str, soup: BeautifulSoup, netloc: str) -> list[str]:
        links: list[str] = []
        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()
            if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
                continue
            full = urljoin(base_url, href)
            p = urlparse(full)
            if p.scheme not in {"http", "https"}:
                continue
            if self.config.same_domain_only and p.netloc != netloc:
                continue
            # strip fragments/queries for dedupe
            normalized = f"{p.scheme}://{p.netloc}{p.path.rstrip('/') or '/'}"
            # Skip obvious junk paths
            if any(seg in normalized.lower() for seg in ["/cart", "/account", "/login", "/logout", "/search", ".xml", ".pdf"]):
                continue
            links.append(normalized)
        return dedupe_preserve(links)

    # ---------- extraction ----------

    def _extract(self, url: str, soup: BeautifulSoup) -> _PageExtract | None:
        # Remove noisy nodes
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        title = clean_whitespace(soup.title.text if soup.title else "")
        page_type = self._guess_page_type(url, soup)
        text_body = clean_whitespace(soup.get_text(" "))
        if not text_body:
            return None

        product_name = self._extract_product_name(soup, page_type)
        description = self._extract_description(soup)
        price = self._extract_price(soup, text_body)
        tasting_notes = self._extract_tasting_notes(soup, text_body)
        ingredients = self._extract_ingredients(soup, text_body)
        category = self._guess_category(f"{title} {text_body}")
        is_gift = bool(_GIFT_PATTERNS.search(text_body)) or page_type == "gift_set"
        cta_text = self._extract_ctas(soup)
        hero_headline = self._extract_hero_headline(soup)
        collections = self._extract_collections(soup)
        brand_snippets = self._extract_brand_snippets(soup)

        return _PageExtract(
            url=url,
            page_type=page_type,
            title=truncate(title, 200),
            product_name=product_name,
            product_category=category,
            price=price,
            description=truncate(description, 1200),
            tasting_notes=tasting_notes[:8],
            ingredients=ingredients[:12],
            is_gift_set=is_gift,
            cta_text=cta_text[:8],
            hero_headline=hero_headline,
            featured_collections=collections[:12],
            brand_snippets=brand_snippets[:6],
        )

    def _guess_page_type(self, url: str, soup: BeautifulSoup) -> str:
        low = url.lower()
        if "/products/" in low:
            return "product"
        if "/collections/" in low or "/shop/" in low:
            return "collection"
        if any(seg in low for seg in ["/about", "/story", "/our-story", "/brand"]):
            return "about"
        if any(seg in low for seg in ["/journal", "/blog", "/articles", "/news"]):
            return "blog"
        if any(seg in low for seg in ["/gift", "/gifts", "/bundles"]):
            return "gift_set"
        if low.rstrip("/").endswith(urlparse(low).netloc):
            return "home"
        # Also treat JSON-LD product as product
        if soup.find("script", type="application/ld+json"):
            return "product"
        return "other"

    def _extract_product_name(self, soup: BeautifulSoup, page_type: str) -> str | None:
        if page_type != "product":
            return None
        h1 = soup.find("h1")
        if h1 and h1.text.strip():
            return clean_whitespace(h1.text)
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            return clean_whitespace(og["content"])
        return None

    def _extract_description(self, soup: BeautifulSoup) -> str:
        og = soup.find("meta", property="og:description")
        if og and og.get("content"):
            return clean_whitespace(og["content"])
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            return clean_whitespace(meta["content"])
        # first meaningful paragraph
        for p in soup.find_all("p"):
            txt = clean_whitespace(p.get_text(" "))
            if len(txt) > 80:
                return txt
        return ""

    def _extract_price(self, soup: BeautifulSoup, text_body: str) -> float | None:
        for sel in ["meta[itemprop=price]", "meta[property='product:price:amount']"]:
            node = soup.select_one(sel)
            if node and node.get("content"):
                parsed = parse_price(node["content"])
                if parsed:
                    return parsed
        # Fallback: first price-looking string in body
        m = _PRICE_HINT_RE.search(text_body)
        if m:
            snippet = text_body[m.start() : m.start() + 30]
            return parse_price(snippet)
        return None

    def _extract_tasting_notes(self, soup: BeautifulSoup, text_body: str) -> list[str]:
        notes: list[str] = []
        # Look for list items near a "tasting notes" label
        low = text_body.lower()
        if "tasting note" in low or "notes of" in low:
            for li in soup.find_all("li"):
                t = clean_whitespace(li.get_text(" "))
                if 2 < len(t) < 80:
                    notes.append(t)
        return dedupe_preserve(notes)

    def _extract_ingredients(self, soup: BeautifulSoup, text_body: str) -> list[str]:
        ings: list[str] = []
        if "ingredients" not in text_body.lower():
            return ings
        for tag in soup.find_all(["li", "p"]):
            t = clean_whitespace(tag.get_text(" "))
            if not t:
                continue
            if "ingredients" in t.lower() and ":" in t:
                parts = t.split(":", 1)[1]
                for part in re.split(r"[,;•·]", parts):
                    part = clean_whitespace(part)
                    if 1 < len(part) < 60:
                        ings.append(part)
                break
        return dedupe_preserve(ings)

    def _guess_category(self, text: str) -> str | None:
        low = text.lower()
        for hint in _CATEGORY_HINTS:
            if hint in low:
                return hint
        return None

    def _extract_ctas(self, soup: BeautifulSoup) -> list[str]:
        ctas: list[str] = []
        for node in soup.find_all(["button", "a"]):
            text = clean_whitespace(node.get_text(" "))
            if not text or len(text) > 40:
                continue
            low = text.lower()
            if any(
                kw in low
                for kw in ["buy", "add to", "shop", "gift", "discover", "subscribe", "learn more", "explore"]
            ):
                ctas.append(text)
        return dedupe_preserve(ctas)

    def _extract_hero_headline(self, soup: BeautifulSoup) -> str | None:
        h1 = soup.find("h1")
        if h1:
            txt = clean_whitespace(h1.get_text(" "))
            if txt and len(txt) < 180:
                return txt
        return None

    def _extract_collections(self, soup: BeautifulSoup) -> list[str]:
        names: list[str] = []
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if "/collections/" in href:
                text = clean_whitespace(a.get_text(" "))
                if 2 < len(text) < 60:
                    names.append(text)
        return dedupe_preserve(names)

    def _extract_brand_snippets(self, soup: BeautifulSoup) -> list[str]:
        snippets: list[str] = []
        for tag in soup.find_all(["h2", "h3", "p", "blockquote"]):
            t = clean_whitespace(tag.get_text(" "))
            if not t:
                continue
            low = t.lower()
            if any(
                kw in low
                for kw in [
                    "our story",
                    "we believe",
                    "crafted",
                    "single origin",
                    "sourced",
                    "artisan",
                    "heritage",
                    "ceremonial",
                    "our mission",
                ]
            ) and len(t) < 400:
                snippets.append(t)
        return dedupe_preserve(snippets)
