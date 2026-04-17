"""Meta Graph API connector for Facebook Pages and Instagram Business.

Uses the official Graph API — never scrapes. Auth is via long-lived access
token in env (META_ACCESS_TOKEN). This is a real connector shape; endpoints
actually call the Graph API if credentials are configured. If credentials
are missing or insights permissions are absent, it returns a clear error
and documents which fields are unavailable.

Required permissions (documented here for the operator):
- Facebook Pages: `pages_read_engagement`, `pages_show_list`, `read_insights`
- Instagram Business: `instagram_basic`, `instagram_manage_insights`,
  `pages_read_engagement`, `business_management`
- The token must be a Page-scoped or System-User token with the linked
  Instagram Business account.

Notes on limitations:
- Instagram does NOT expose saves via most public endpoints; `saved` insight
  is available for IG Business/Creator accounts through Graph insights.
- `shares` for IG posts is limited and varies by media type.
- Reach/impressions are insight fields; require `read_insights` permission.
- Organic vs paid decomposition is not in scope here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests

from config import get_settings
from connectors.base import IngestionResult, MetricAvailability
from models import MediaType, Platform, Post, PostMetrics
from utils.logging import log_event


class MetaGraphError(RuntimeError):
    pass


IG_INSIGHT_METRICS = ["impressions", "reach", "saved", "likes", "comments", "shares", "video_views"]
FB_INSIGHT_METRICS = [
    "post_impressions",
    "post_impressions_unique",
    "post_reactions_by_type_total",
    "post_clicks",
]


@dataclass
class MetaConfig:
    access_token: str
    fb_page_id: str | None
    ig_user_id: str | None
    graph_version: str
    timeout: int = 20

    @classmethod
    def from_env(cls) -> "MetaConfig":
        s = get_settings()
        if not s.meta_access_token:
            raise MetaGraphError(
                "META_ACCESS_TOKEN is not set. Add it to your environment or .env file."
            )
        return cls(
            access_token=s.meta_access_token,
            fb_page_id=s.meta_fb_page_id,
            ig_user_id=s.meta_ig_user_id,
            graph_version=s.meta_graph_version,
            timeout=15,
        )


class MetaGraphConnector:
    """Thin Graph API client. One public fetch per platform."""

    BASE = "https://graph.facebook.com"

    def __init__(self, config: MetaConfig | None = None) -> None:
        self.config = config or MetaConfig.from_env()
        self._session = requests.Session()

    # ---------- high level ----------

    def fetch_instagram_posts(self, limit: int = 25) -> IngestionResult:
        result = IngestionResult()
        if not self.config.ig_user_id:
            result.errors.append(
                "META_IG_USER_ID is not set. Add the Instagram Business user ID to .env."
            )
            return result
        try:
            media = self._get(
                f"/{self.config.ig_user_id}/media",
                params={
                    "fields": (
                        "id,caption,media_type,media_product_type,permalink,"
                        "timestamp,like_count,comments_count"
                    ),
                    "limit": limit,
                },
            )
        except MetaGraphError as e:
            result.errors.append(str(e))
            return result

        for item in media.get("data", []):
            post = self._ig_item_to_post(item)
            result.posts.append(post)
        return result

    def fetch_facebook_posts(self, limit: int = 25) -> IngestionResult:
        result = IngestionResult()
        if not self.config.fb_page_id:
            result.errors.append(
                "META_FB_PAGE_ID is not set. Add the Facebook Page ID to .env."
            )
            return result
        try:
            feed = self._get(
                f"/{self.config.fb_page_id}/posts",
                params={
                    "fields": (
                        "id,message,created_time,permalink_url,attachments{media_type},"
                        "reactions.summary(total_count),comments.summary(total_count),"
                        "shares"
                    ),
                    "limit": limit,
                },
            )
        except MetaGraphError as e:
            result.errors.append(str(e))
            return result

        for item in feed.get("data", []):
            post = self._fb_item_to_post(item)
            result.posts.append(post)
        return result

    def metric_availability(self, platform: Platform) -> MetricAvailability:
        """Declare what the Graph API can and cannot give us per platform."""
        if platform == Platform.INSTAGRAM:
            return MetricAvailability(
                available=[
                    "impressions (with read_insights)",
                    "reach (with read_insights)",
                    "likes",
                    "comments",
                    "saves (IG insight: `saved`)",
                    "shares (limited by media type)",
                    "video_views",
                ],
                unavailable=["clicks (not exposed for organic IG)", "conversions", "revenue"],
                notes=[
                    "Insights endpoint requires Instagram Business/Creator.",
                    "Saves and shares require `instagram_manage_insights`.",
                ],
            )
        if platform == Platform.FACEBOOK:
            return MetricAvailability(
                available=[
                    "impressions / reach (post_impressions*)",
                    "reactions (summary count)",
                    "comments count",
                    "shares count",
                    "post_clicks (insight)",
                ],
                unavailable=["saves (not a FB concept)", "conversions", "revenue"],
                notes=[
                    "Impressions need `read_insights`.",
                    "Organic/paid split requires additional metric suffixes.",
                ],
            )
        return MetricAvailability()

    # ---------- low level ----------

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.BASE}/{self.config.graph_version}{path}"
        params = {**params, "access_token": self.config.access_token}
        try:
            resp = self._session.get(url, params=params, timeout=self.config.timeout)
        except requests.RequestException as e:
            log_event("meta_graph_network_error", path=path, error=str(e))
            raise MetaGraphError(f"Network error calling Meta Graph: {e}") from e

        if resp.status_code >= 400:
            snippet = resp.text[:400]
            log_event(
                "meta_graph_http_error",
                path=path,
                status=resp.status_code,
                body_snippet=snippet,
            )
            raise MetaGraphError(
                f"Meta Graph {resp.status_code}: {snippet}"
            )
        try:
            return resp.json()
        except ValueError as e:
            raise MetaGraphError(f"Meta Graph returned non-JSON: {e}") from e

    # ---------- normalizers ----------

    def _ig_item_to_post(self, item: dict[str, Any]) -> Post:
        media_type = (item.get("media_type") or "").lower()
        product_type = (item.get("media_product_type") or "").lower()
        mt = MediaType.IMAGE
        if media_type == "video":
            mt = MediaType.REEL if product_type == "reels" else MediaType.VIDEO
        elif media_type == "carousel_album":
            mt = MediaType.CAROUSEL
        elif media_type == "image":
            mt = MediaType.IMAGE

        created = item.get("timestamp")
        dt = None
        if created:
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except ValueError:
                dt = None

        metrics = PostMetrics(
            likes=item.get("like_count"),
            comments=item.get("comments_count"),
        )
        return Post(
            id=item["id"],
            platform=Platform.INSTAGRAM,
            created_at=dt,
            caption=item.get("caption"),
            media_type=mt,
            permalink=item.get("permalink"),
            metrics=metrics,
            source="meta_instagram",
            raw=item,
        )

    def _fb_item_to_post(self, item: dict[str, Any]) -> Post:
        attachments = item.get("attachments", {}).get("data", [])
        mt = MediaType.UNKNOWN
        if attachments:
            att_type = (attachments[0].get("media_type") or "").lower()
            if att_type == "photo":
                mt = MediaType.IMAGE
            elif att_type == "video":
                mt = MediaType.VIDEO
            elif att_type == "album":
                mt = MediaType.CAROUSEL
            elif att_type == "link":
                mt = MediaType.TEXT

        reactions = (item.get("reactions") or {}).get("summary", {}).get("total_count")
        comments = (item.get("comments") or {}).get("summary", {}).get("total_count")
        shares = (item.get("shares") or {}).get("count")

        dt = None
        created = item.get("created_time")
        if created:
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except ValueError:
                dt = None

        return Post(
            id=item["id"],
            platform=Platform.FACEBOOK,
            created_at=dt,
            caption=item.get("message"),
            media_type=mt,
            permalink=item.get("permalink_url"),
            metrics=PostMetrics(reactions=reactions, comments=comments, shares=shares),
            source="meta_facebook",
            raw=item,
        )
