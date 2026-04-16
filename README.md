# mkt101

AI Marketing Assistant CLI for a middle-to-high-end tea brand. Wraps a structured marketing-assistant spec around the Anthropic SDK so the founder, internal team, or executives can paste in social performance data and get back: clarifying questions (when inputs are thin), performance analysis, 10-15 post ideas, self-critique, top 3 selections, and execution-ready outputs.

## Setup

Requires Python 3.10+ and an Anthropic API key.

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python tea_assistant.py
```

## Commands

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
