# mkt101 — premium tea brand marketing operator

An internal decision-support tool for a middle-to-high-end tea e-commerce brand. Helps the founder, internal marketing team, and executives run a disciplined weekly workflow:

**Data → Analysis → Ideas → Critique → Top 3 → Approval → Calendar**

It is not an autopost bot. It is an opinionated operator dashboard that separates facts from interpretations, protects premium positioning, and keeps a human in the loop before anything ships.

---

## What's in V2

- Modular Streamlit app (`app.py`) with one page per workflow step
- Persistent brand profile (positioning, audience, tone, pillars, guardrails, forbidden hooks)
- Multi-source ingestion: CSV upload, manual table, pasted text, website crawler, Meta Graph API
- Structured LLM orchestration: separate prompts for analysis, idea generation, critique, top-3 selection, execution briefs, and SOP/dashboard
- 7-dimension transparent idea scoring with weighted totals (`brand_fit`, `audience_relevance`, `engagement_potential`, `conversion_support`, `originality`, `production_ease`, `premium_safety`)
- Approval workflow with a state machine (`draft → needs_review → approved → scheduled → posted / rejected`) and an auditable decision log
- Content calendar with weekly view and status transitions
- Native charts for format, pillar, saves-vs-clicks-vs-conversions, top/bottom posts
- Local JSON-file storage under `data/` — transparent, inspectable, easy to swap for SQLite later
- Structured JSON-lines logging under `data/logs/app.jsonl`
- Polite website crawler (requests + BeautifulSoup, robots.txt, rate limiting)
- Meta Graph API connector with clear status of available vs unavailable metrics per platform

---

## Setup

Requires Python 3.10+.

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY at minimum

streamlit run app.py
```

Optional Meta credentials go in the same `.env`. The Meta tab degrades gracefully when they are missing.

### Legacy CLI

`python tea_assistant.py` still works — it's the original chat-style CLI. For the operator UI, use `streamlit run app.py`. The old `streamlit run tea_assistant_ui.py` command now redirects to `app.py`.

---

## File structure

```
app.py                  # Streamlit entry point
tea_assistant.py        # legacy CLI (kept for back-compat)
tea_assistant_ui.py     # legacy UI shim (delegates to app.py)
requirements.txt
.env.example
config/                 # env-driven settings
models/                 # Pydantic data models
storage/                # JSON-file repository
services/               # LLM orchestration + approval + scoring
connectors/             # CSV + Meta Graph ingestion
crawlers/               # website crawler
prompts/                # system + step-specific prompt templates
ui/
  sidebar.py            # sidebar (brand snapshot, data freshness, credentials)
  components.py         # shared cards, badges, dataframes
  pages/                # one module per workflow page
utils/                  # logging, text helpers
data/                   # JSON state, created on first run
```

---

## Architecture notes

**Why JSON files for storage.** A single premium brand's marketing data is tiny; full-file read/write is fine and keeps the state human-readable. Every entity type lives in one file under `data/`, so debugging is just `cat data/ideas.json`. SQLite would be better if multiple operators used this concurrently, but that isn't V2's use case.

**Why multi-step orchestration beats one big prompt.** Each LLM step has a narrow contract (strict JSON schema, limited context, specific rule set). This keeps hallucination low, lets each step be regenerated independently, and makes failures diagnosable. The core system prompt is long but stable, so it sits in the Anthropic prompt cache.

**Why an approval state machine.** The brief explicitly called for approval-first. The state machine in `services/approval.py` is the single choke point for idea status changes; every transition writes a decision log entry.

**Why a dedicated scoring rubric.** Premium brand perception gets the highest weight (0.20) alongside conversion support (0.17) and brand fit (0.18). Scoring is deterministic given the model's values — `IdeaScore.total()` is the arithmetic of record. The model scores, but the weights live in code.

**Why we don't autopost.** Doing so would require credentialed posting with real risk of brand damage on failure. V2 builds the status machine, calendar, and audit trail for an autopost pipeline, but execution stays human.

---

## Data models

All Pydantic v2. Key types in `models/`:

- `BrandProfile` — single-record brand memory with pillars, constraints, guardrails, forbidden hooks
- `Post` + `PostMetrics` — normalized across IG and FB; missing metrics stay `None` (never fabricated)
- `ContentIdea` — includes `IdeaScore`, `IdeaCritique`, optional `ExecutionBrief`, status, top-3 flag + reason
- `CalendarEntry` — links to an idea or holds ad-hoc entries
- `SyncRun` — every ingestion run (CSV, crawl, Meta) logs one
- `SourceRecord` — crawled pages, product records, pasted notes
- `DecisionLogEntry` — audit trail for any idea/calendar state transition

---

## LLM behavior and prompt design

`prompts/system.py` holds the non-negotiable operating rules: fact/interpretation/assumption/recommendation separation, premium guardrails, platform awareness, no-fluff output style. It's large and stable so it stays cached across turns.

Each workflow step has its own user-template prompt + JSON schema:

- `prompts/analysis.py` — performance analysis with evidence-cited working/failing signals
- `prompts/ideas.py` — 10–15 distinct, evidence-referenced ideas
- `prompts/critique.py` — full 7-dim scoring per idea
- `prompts/top3.py` — top-3 selection with explicit `beats_rejected` comparisons
- `prompts/briefs.py` — production-ready execution brief per selected idea
- `prompts/sop.py` — weekly SOP + dashboard reading guide

All of these return strict JSON, which the service layer deserializes into Pydantic models. Streaming is used for the streaming UX but the client recovers JSON robustly if the model wraps output in fences.

---

## Website crawler

`crawlers/tea_site.py` is brand-focused: given a start URL, it does a BFS within the same domain, respects robots.txt, rate-limits, and extracts:

- product name, category, price, description, tasting notes, ingredients
- gift-set / bundle signal
- CTAs, hero headlines, featured collections
- brand language snippets (sourcing, heritage, craft, ceremonial, etc.)

Output is dict-per-page and gets stored as `SourceRecord`s. Downloadable as CSV from the UI. Playwright is not used; it can be added under `crawlers/` later if dynamic rendering becomes necessary.

---

## Meta Graph API connector

`connectors/meta_graph.py` is the real connector shape — it calls `graph.facebook.com/v21.0/...` with env-based auth.

**You need to provide:**
- `META_ACCESS_TOKEN` — long-lived page or system-user token
- `META_FB_PAGE_ID` — Facebook Page ID
- `META_IG_USER_ID` — Instagram Business user ID (linked to the FB Page)

**Required permissions:**
- Pages: `pages_read_engagement`, `pages_show_list`, `read_insights`
- Instagram Business: `instagram_basic`, `instagram_manage_insights`, `pages_read_engagement`, `business_management`

**Metric availability (documented in `metric_availability()` and surfaced in the UI):**
- Instagram: `impressions`, `reach`, `saved`, `likes`, `comments`, `shares` (limited), `video_views`. Clicks/conversions/revenue are **not** exposed for organic IG.
- Facebook: `post_impressions*`, reactions summary, comments count, `shares.count`, `post_clicks`. Saves is not a FB concept.

Insights require a Business / Creator account. The current connector does not call the separate `/insights` endpoints; it pulls the core fields first so the app works with a minimal token. Add `/insights` extensions under `MetaGraphConnector` once the required permissions are approved.

---

## Weekly SOP (generated + stable template)

The **SOP / Dashboard Logic** page generates a brand-specific SOP from the current analysis. A generic starting template:

1. **Mon** — pull last week's Meta data, validate freshness, run performance analysis
2. **Tue** — generate 10–15 ideas, critique and score
3. **Wed** — pick top 3, write execution briefs, share for approval
4. **Thu** — team reviews & approves / rejects / requests edits
5. **Fri** — production: shoot / design / edit
6. **following week** — scheduled posts go live; log observed KPIs; feed back into next analysis

---

## Known limitations & next steps

- **No insights endpoint yet.** Meta Graph connector pulls core post fields; `GET /{post-id}/insights?metric=...` should be added once permissions are granted. Shape is already there; just add an `_enrich_with_insights` call after `fetch_*`.
- **No auth on the app itself.** V2 assumes local or trusted network use. Add Streamlit auth or reverse-proxy auth before deploying shared.
- **JSON storage is single-writer.** Fine for one operator at a time. If concurrent editing is needed, migrate `storage/repo.py` to SQLite (Repository is the only boundary to change).
- **Crawler has no JS rendering.** If the brand site is Shopify or WordPress it will almost always work. For heavy client-rendered sites, add a Playwright fallback under `crawlers/`.
- **Google Docs / Sheets export** is not implemented; execution briefs and SOPs can be downloaded as JSON and copy-pasted. Native export + `gspread` is a clean V2.1 add.
- **Shopify / Google Analytics** connectors are not in this release but the ingestion shape (`connectors/base.py`, `SyncRun`, `Post`) is built to accept them — add a new module per source.
- **Autoposting is off by default.** `ALLOW_AUTOPOST` env flag exists and lights a warning in the sidebar, but no posting code is wired up. Approval-first is the V2 stance.

---

## Decision summary

| Decision | Choice | Reason |
|---|---|---|
| Storage | Local JSON files | Transparent, single-operator scale, no migrations |
| Models | Pydantic v2 | Typed, validating, plays well with Streamlit |
| UI | Streamlit radio nav + per-page modules | Keeps pages focused, trivial to extend |
| LLM | Claude Opus 4.7 + adaptive thinking, effort=high | Highest-quality structured reasoning; cached system prompt |
| Prompts | One per step, strict JSON schema | Deterministic contracts, easy to regenerate one step |
| Crawler | requests + BeautifulSoup | Sufficient for typical tea e-commerce sites |
| Meta | Official Graph API, env-var auth | Compliance + reliability vs. scraping |
| Autopost | Disabled | Brand-safety + approval discipline |

---

## Quick sanity check

After install:

```bash
streamlit run app.py
# → open Brand Profile, fill in the basics
# → Data Sources → paste a small CSV or the sample in the prior README
# → Performance Analysis → Run
# → Idea Generation → Generate
# → Idea Critique & Scoring → Critique & score
# → Top 3 Recommendations → Pick top 3 → Generate brief → Approve → Add to calendar
```

Everything is stored under `data/` and `data/logs/`.
