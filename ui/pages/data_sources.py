"""Data Sources page: CSV upload, manual entry, pasted text, website crawl, Meta sync."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd
import streamlit as st

from config import get_settings
from connectors import ColumnMapping, CsvIngestor, MetaGraphConnector, MetaGraphError
from crawlers import CrawlConfig, TeaSiteCrawler
from models import (
    MediaType,
    Platform,
    Post,
    PostMetrics,
    SourceRecord,
    SourceType,
    SyncRun,
    SyncSource,
    SyncStatus,
)
from storage import get_repository
from utils.logging import log_event


def render() -> None:
    st.header("Data Sources")
    st.caption("Ingest from CSV, the brand website, or Meta Graph. All runs show up in *Sync / Logs / Status*.")

    tab_csv, tab_manual, tab_paste, tab_crawl, tab_meta = st.tabs(
        ["CSV upload", "Manual table", "Paste metrics", "Website crawl", "Meta Graph"]
    )

    with tab_csv:
        _render_csv_tab()
    with tab_manual:
        _render_manual_tab()
    with tab_paste:
        _render_paste_tab()
    with tab_crawl:
        _render_crawl_tab()
    with tab_meta:
        _render_meta_tab()


def _render_csv_tab() -> None:
    st.subheader("CSV upload")
    st.caption(
        "Upload any CSV of posts. Map the columns, preview the normalized data, and commit."
    )
    uploaded = st.file_uploader("Choose a CSV", type=["csv"])
    if not uploaded:
        return

    try:
        df = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        return

    st.write("Preview of raw file (first 10 rows):")
    st.dataframe(df.head(10), use_container_width=True)

    headers = list(df.columns)
    guess = ColumnMapping.default_guess(headers)

    st.markdown("**Column mapping**")
    st.caption("Defaults are guessed from header names. Leave a field blank if your file doesn't have it.")

    def _select(label: str, current: str | None) -> str | None:
        options = ["(none)"] + headers
        default_idx = options.index(current) if current in options else 0
        val = st.selectbox(label, options=options, index=default_idx, key=f"map_{label}")
        return None if val == "(none)" else val

    cols = st.columns(3)
    with cols[0]:
        guess.id = _select("post id", guess.id)
        guess.platform = _select("platform", guess.platform)
        guess.created_at = _select("created_at", guess.created_at)
        guess.caption = _select("caption", guess.caption)
        guess.media_type = _select("media_type", guess.media_type)
    with cols[1]:
        guess.permalink = _select("permalink", guess.permalink)
        guess.pillar = _select("pillar", guess.pillar)
        guess.format_label = _select("format_label", guess.format_label)
        guess.impressions = _select("impressions", guess.impressions)
        guess.reach = _select("reach", guess.reach)
    with cols[2]:
        guess.likes = _select("likes", guess.likes)
        guess.comments = _select("comments", guess.comments)
        guess.shares = _select("shares", guess.shares)
        guess.saves = _select("saves", guess.saves)
        guess.clicks = _select("clicks", guess.clicks)

    if st.button("Normalize and preview", use_container_width=True):
        ingestor = CsvIngestor()
        result = ingestor.ingest_rows(df.to_dict(orient="records"), guess)
        st.session_state["csv_preview"] = result

    preview = st.session_state.get("csv_preview")
    if preview:
        st.markdown("**Normalized preview**")
        from ui.components import posts_to_dataframe

        st.dataframe(posts_to_dataframe(preview.posts), use_container_width=True)
        st.caption(
            f"{len(preview.posts)} posts · {preview.skipped} skipped · {len(preview.errors)} errors"
        )
        if preview.errors:
            with st.expander("Errors"):
                for err in preview.errors:
                    st.write(f"• {err}")
        if st.button("Commit to store", type="primary", use_container_width=True, key="commit_csv"):
            repo = get_repository()
            run = SyncRun(source=SyncSource.CSV)
            repo.save_sync(run)
            added = repo.upsert_posts(preview.posts)
            run.records_ingested = added
            run.records_skipped = preview.skipped
            run.finish(
                SyncStatus.OK if not preview.errors else SyncStatus.PARTIAL,
                f"CSV: {added} upserted, {preview.skipped} skipped",
            )
            run.errors = preview.errors
            repo.save_sync(run)
            st.session_state.pop("csv_preview", None)
            st.success(f"Ingested {added} posts.")
            log_event("csv_ingest", added=added, skipped=preview.skipped)


def _render_manual_tab() -> None:
    st.subheader("Manual table entry")
    st.caption("Type or paste rows directly. Good for a quick weekly review.")

    template = pd.DataFrame(
        [
            {
                "id": "",
                "platform": "instagram",
                "created_at": "",
                "caption": "",
                "media_type": "reel",
                "pillar": "",
                "reach": None,
                "likes": None,
                "comments": None,
                "shares": None,
                "saves": None,
                "clicks": None,
            }
        ]
    )
    edited = st.data_editor(
        template,
        num_rows="dynamic",
        use_container_width=True,
        key="manual_editor",
    )

    if st.button("Ingest manual rows", use_container_width=True):
        ingestor = CsvIngestor()
        mapping = ColumnMapping.default_guess(list(edited.columns))
        result = ingestor.ingest_rows(edited.to_dict(orient="records"), mapping)
        repo = get_repository()
        run = SyncRun(source=SyncSource.MANUAL)
        repo.save_sync(run)
        added = repo.upsert_posts(result.posts)
        run.records_ingested = added
        run.records_skipped = result.skipped
        run.finish(
            SyncStatus.OK if not result.errors else SyncStatus.PARTIAL,
            f"Manual: {added} upserted",
        )
        run.errors = result.errors
        repo.save_sync(run)
        st.success(f"Ingested {added} rows.")
        if result.errors:
            st.warning("\n".join(result.errors[:5]))


def _render_paste_tab() -> None:
    st.subheader("Paste raw metrics")
    st.caption(
        "Drop an unstructured block of metrics. Stored as a note the assistant can read. "
        "Use CSV upload or Manual table for structured metrics."
    )
    raw = st.text_area("Paste here", height=200, placeholder="Last 7 IG posts (reach/likes/saves/comments)...")
    if st.button("Save as source note", use_container_width=True):
        if not raw.strip():
            st.warning("Nothing to save.")
            return
        repo = get_repository()
        run = SyncRun(source=SyncSource.PASTED_TEXT)
        record = SourceRecord(
            source_type=SourceType.NOTE,
            source_run_id=run.id,
            title=f"Pasted metrics {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
            content=raw.strip(),
            tags=["pasted", "metrics"],
        )
        repo.add_sources([record])
        run.records_ingested = 1
        run.finish(SyncStatus.OK, "Saved pasted text as source note")
        repo.save_sync(run)
        st.success("Saved.")


def _render_crawl_tab() -> None:
    st.subheader("Website crawl")
    st.caption(
        "Polite requests + BeautifulSoup. Respects robots.txt. "
        "Extracts products, pillars, CTAs, hero headlines, and brand language."
    )
    settings = get_settings()

    cols = st.columns([2, 1, 1, 1])
    url = cols[0].text_input("Start URL or domain", value="")
    max_pages = cols[1].number_input("Max pages", 5, 500, value=settings.crawler_max_pages)
    rate = cols[2].number_input(
        "Rate limit (s/request)", 0.2, 10.0, value=settings.crawler_rate_limit_seconds, step=0.1
    )
    respect = cols[3].checkbox("Respect robots.txt", value=True)

    if st.button("Start crawl", type="primary", use_container_width=True, disabled=not url):
        config = CrawlConfig(
            start_url=url,
            max_pages=int(max_pages),
            rate_limit_seconds=float(rate),
            respect_robots=respect,
        )
        crawler = TeaSiteCrawler(config)
        repo = get_repository()
        run = SyncRun(source=SyncSource.WEBSITE_CRAWL, params={"url": url, "max_pages": int(max_pages)})
        repo.save_sync(run)

        progress = st.progress(0.0, text="starting…")
        status_line = st.empty()

        def on_progress(done: int, total: int, last_url: str) -> None:
            progress.progress(min(1.0, done / max(1, total)), text=f"{done}/{total}: {last_url}")
            status_line.caption(f"last: {last_url}")

        try:
            result = crawler.crawl(on_progress=on_progress)
        except Exception as e:
            run.finish(SyncStatus.FAILED, f"Crawler error: {e}")
            repo.save_sync(run)
            st.error(f"Crawl failed: {e}")
            return

        progress.progress(1.0, text="done")
        records = [
            SourceRecord(
                source_type=SourceType.PRODUCT if p["page_type"] == "product" else SourceType.WEBSITE_PAGE,
                source_run_id=run.id,
                url=p["page_url"],
                title=p["title"] or p.get("product_name") or p["page_url"],
                content=p.get("description", ""),
                structured=p,
                tags=[p["page_type"]],
            )
            for p in result.pages
        ]
        added = repo.add_sources(records)
        run.records_ingested = added
        run.records_skipped = len(result.pages) - added
        run.errors = result.errors
        run.finish(
            SyncStatus.OK if not result.errors else SyncStatus.PARTIAL,
            f"Crawled {len(result.fetched_urls)} URLs, stored {added} new.",
        )
        repo.save_sync(run)
        st.session_state["last_crawl"] = result
        st.success(f"Stored {added} new source records from {len(result.fetched_urls)} pages.")
        if result.robots_blocked:
            st.info(f"{len(result.robots_blocked)} URLs blocked by robots.txt.")

    result = st.session_state.get("last_crawl")
    if result and result.pages:
        df = pd.DataFrame(result.pages)
        st.markdown("**Preview**")
        st.dataframe(df, use_container_width=True)
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name=f"crawl_{uuid4().hex[:6]}.csv",
            mime="text/csv",
        )


def _render_meta_tab() -> None:
    st.subheader("Meta Graph (Facebook + Instagram Business)")
    settings = get_settings()

    st.caption(
        "Uses the official Graph API — no scraping. Set credentials via environment "
        "variables: `META_ACCESS_TOKEN`, `META_FB_PAGE_ID`, `META_IG_USER_ID`."
    )

    creds_cols = st.columns(3)
    creds_cols[0].metric("Access token", "set" if settings.meta_access_token else "missing")
    creds_cols[1].metric("FB Page ID", settings.meta_fb_page_id or "—")
    creds_cols[2].metric("IG User ID", settings.meta_ig_user_id or "—")

    st.markdown(
        "**Required permissions:** `pages_read_engagement`, `pages_show_list`, `read_insights` for Pages; "
        "`instagram_basic`, `instagram_manage_insights`, `business_management` for Instagram Business. "
        "Insights (reach, impressions, saves) require a Business / Creator account."
    )

    limit = st.number_input("Posts per platform to fetch", 1, 100, value=25)

    sync_cols = st.columns(2)
    if sync_cols[0].button("Sync Instagram", use_container_width=True, disabled=not settings.meta_access_token):
        _run_meta_sync(Platform.INSTAGRAM, int(limit))
    if sync_cols[1].button("Sync Facebook", use_container_width=True, disabled=not settings.meta_access_token):
        _run_meta_sync(Platform.FACEBOOK, int(limit))

    if not settings.meta_access_token:
        st.warning(
            "No `META_ACCESS_TOKEN` in environment. Add it to your .env and restart to enable syncs."
        )

    st.markdown("---")
    st.markdown("**Metric availability by platform**")
    try:
        connector = MetaGraphConnector()
        ig_avail = connector.metric_availability(Platform.INSTAGRAM)
        fb_avail = connector.metric_availability(Platform.FACEBOOK)
    except MetaGraphError:
        # no token; still show schema
        class _Shim:
            def metric_availability(self, p):
                return MetaGraphConnector.__dict__["metric_availability"](
                    type("X", (), {"config": None})(), p
                )

        ig_avail = _Shim().metric_availability(Platform.INSTAGRAM)
        fb_avail = _Shim().metric_availability(Platform.FACEBOOK)

    cols = st.columns(2)
    for col, platform_name, avail in [
        (cols[0], "Instagram", ig_avail),
        (cols[1], "Facebook", fb_avail),
    ]:
        with col:
            st.markdown(f"**{platform_name}**")
            st.caption("Available: " + ("; ".join(avail.available) or "—"))
            st.caption("Unavailable: " + ("; ".join(avail.unavailable) or "—"))
            for n in avail.notes:
                st.caption("note · " + n)


def _run_meta_sync(platform: Platform, limit: int) -> None:
    repo = get_repository()
    source = SyncSource.META_INSTAGRAM if platform == Platform.INSTAGRAM else SyncSource.META_FACEBOOK
    run = SyncRun(source=source, params={"limit": limit})
    repo.save_sync(run)
    try:
        connector = MetaGraphConnector()
    except MetaGraphError as e:
        run.finish(SyncStatus.FAILED, str(e))
        repo.save_sync(run)
        st.error(str(e))
        return

    try:
        if platform == Platform.INSTAGRAM:
            result = connector.fetch_instagram_posts(limit=limit)
        else:
            result = connector.fetch_facebook_posts(limit=limit)
    except Exception as e:
        run.finish(SyncStatus.FAILED, f"Sync error: {e}")
        repo.save_sync(run)
        st.error(f"Sync error: {e}")
        return

    if result.errors and not result.posts:
        run.errors = result.errors
        run.finish(SyncStatus.FAILED, "; ".join(result.errors))
        repo.save_sync(run)
        st.error("\n".join(result.errors))
        return

    added = repo.upsert_posts(result.posts)
    run.records_ingested = added
    run.records_skipped = len(result.posts) - added
    run.errors = result.errors
    run.finish(
        SyncStatus.OK if not result.errors else SyncStatus.PARTIAL,
        f"{platform.value}: {added} new posts",
    )
    repo.save_sync(run)
    if result.errors:
        st.warning("\n".join(result.errors))
    st.success(f"Ingested {added} posts from {platform.value}.")
