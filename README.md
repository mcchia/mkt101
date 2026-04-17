# mkt101

AI Marketing Assistant for a middle-to-high-end tea brand. Wraps a structured marketing-assistant spec around the Anthropic SDK so the founder, internal team, or executives can paste in social performance data and get back: clarifying questions (when inputs are thin), performance analysis, 10-15 post ideas, self-critique, top 3 selections, and execution-ready outputs.

Ships with both a CLI (`tea_assistant.py`) and a Streamlit web UI (`tea_assistant_ui.py`).

## Setup

Requires Python 3.10+ and an Anthropic API key.

```bash
pip install -r requirements.txt

# Provide your key via ONE of the options in 'Security setup' below.
python tea_assistant.py              # CLI
streamlit run tea_assistant_ui.py    # Web UI
```

## Security setup

Credentials are loaded by `config.get_api_key()` in this order:

1. `ANTHROPIC_API_KEY` in the process environment
2. `.streamlit/secrets.toml` (Streamlit UI only)
3. `.env` in the project root (loaded via `python-dotenv`)

Pick one of these:

**Option A — `.env` file (recommended for local dev)**

```bash
cp .env.example .env
# edit .env and replace sk-ant-REPLACE_ME with your real key
```

**Option B — Streamlit secrets (recommended for Streamlit Cloud)**

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit and replace sk-ant-REPLACE_ME with your real key
```

**Option C — process environment**

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### Rules

- Never paste your key into source files, commit messages, prompts, or chat
  content. The chat history is sent to Anthropic and stored in Streamlit
  session state.
- `.env`, `.env.*`, and `.streamlit/secrets.toml` are all listed in
  `.gitignore`. Do not force-add them.
- Error messages shown in the CLI and UI are passed through a redactor
  (`config.redact`) that scrubs anything matching common API-key shapes.
- If you suspect a key was exposed (committed, pasted, screen-shared, logged,
  shared in a support ticket, etc.), rotate it immediately at
  <https://console.anthropic.com/settings/keys> and update your local
  `.env` / secrets file. Revoking a key invalidates it on Anthropic's side;
  simply removing it from a file or a commit does **not**.

### If you have already committed a key

Git history is effectively public once pushed. Do the following, in order:

1. **Rotate the key first.** Revoke the exposed key in the Anthropic console
   and issue a new one. Everything else is secondary.
2. Update your local `.env` / `.streamlit/secrets.toml` with the new key.
3. Optionally purge the secret from history with `git filter-repo` or the
   BFG Repo-Cleaner, then force-push. This does **not** un-leak the old key —
   only rotation does.

## Web UI

`streamlit run tea_assistant_ui.py` opens a multipage app in the browser. Pages:

- **Assistant** — the original chat (analyze → ideate → critique → top 3 → execute). Automatically consumes brand memory, recent content history, and winning/losing patterns.
- **Templates** — one-click workflows (weekly analysis, monthly review, campaign kickoff, product launch, gifting season). Custom templates can be saved.
- **Seasonal Planner** — calendar-aware plans for Tet, Mid-Autumn, corporate gifting, holiday gift boxes, and wellness windows.
- **A/B Testing** — generate two on-brand variants for a selected concept along a named dimension (hook / caption / format / CTA).
- **Brand Memory** — editable truth (tone, audience, pillars, guardrails, banned phrases, CTA style, positioning notes, constraints) separate from inferred suggestions.
- **Content History** — track hook / angle / format / CTA / pillar across posts, with CSV bulk import and fatigue detection.
- **Patterns & Losing Posts** — extract winning and losing patterns by metric (reach, likes, saves, comments, clicks, orders, or a weighted score), with strong- vs thin-evidence separation and stop/reduce/retest recommendations.
- **Brand Protection** — rule-based + optional LLM checker with a transparent score, category, severity, excerpt, and reason per flag.
- **Competitor Watch** — manual-first competitor records, optional conservative public-URL fetch, and whitespace-oriented insights that do not copy competitor content.
- **Sync Scheduler** — configure a daily sync (enable flag, time of day, sources) with last/next-run indicators. A standalone runner `python -m scripts.run_sync` can be driven by cron for true automation.

## Local state

All app state (brand memory, content history, A/B plans, competitors, seasonal plans, templates, protection logs, scheduler settings/history) persists as JSON in `./data/`. The directory is gitignored. Set `TEA_DATA_DIR` to relocate.

No credentials or prompt content are ever written to `./data/`. Scheduler run history stores only metadata and a short, safe summary per source.

## Daily sync via cron (optional)

```bash
# crontab -e
0 8 * * *  cd /path/to/mkt101 && /path/to/venv/bin/python -m scripts.run_sync >> /tmp/mkt101_sync.log 2>&1
```

The runner reads `ANTHROPIC_API_KEY` exactly like the app (env / `.env` / Streamlit secrets) and writes only metadata to `data/scheduler_history.json`. It never logs the key, prompt content, or URLs with query strings.

## CLI commands

| Command  | Purpose                                                          |
| -------- | ---------------------------------------------------------------- |
| `:paste` | Multi-line input. Paste content, then type `END` on a new line.  |
| `:reset` | Clear conversation history and start fresh.                      |
| `:quit`  | Exit.                                                            |

A single-line message is sent on Enter.

## Example session

```
$ python tea_assistant.py
AI Marketing Assistant — tea brand
Commands: :paste (multi-line input), :reset, :quit

You> :paste
(paste mode — type END on its own line to submit)
Last 7 IG posts (reach / likes / saves / comments):
1. Oolong brewing reel — 18.2k / 920 / 240 / 41
2. Founder story carousel — 4.1k / 310 / 18 / 7
3. Gift box flat lay — 6.8k / 410 / 35 / 12
4. Tea + ceramics pairing reel — 22.5k / 1.4k / 380 / 56
5. "Why we don't use teabags" text post — 2.9k / 180 / 9 / 4
6. Customer UGC repost — 3.4k / 240 / 12 / 6
7. Single-origin sourcing reel — 14.7k / 780 / 190 / 33

Goal: drive saves and DMs from buyers, not just reach.
END

Assistant> 1. Clarifying questions
- Which two or three SKUs do you most want to move this quarter ...
[continues with the structured 8-section output]

[tokens: in=1612 out=4203 cache_read=0 cache_write=0]
```

## Notes

- Model: `claude-opus-4-7` with adaptive thinking and `effort: high`.
- The system prompt sits at ~1.5K tokens, below Opus 4.7's 4096-token cache minimum, so `cache_read` stays at 0 until the conversation history grows past that. Expected, not a bug.
- Streaming is on; long structured outputs render as they generate.
