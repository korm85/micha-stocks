# Micha Stocks — Agent Guide

AI-powered stock decision tool applying pattern-based reasoning from 2,500+ YouTube transcripts with live market data.

## Quick Start

```bash
# Dashboard
cd app
pip install streamlit plotly yfinance requests pandas
streamlit run streamlit_app/app.py --server.port 8501 --server.address 0.0.0.0

# Slide deck
cd deck
pnpm install   # or npm install
pnpm dev       # → http://localhost:5175
```

## Repository Structure

```
micha-stocks/
├── app/                  ← Streamlit dashboard
│   ├── streamlit_app/
│   │   └── app.py       ← Main dashboard (~2100 lines)
│   ├── scripts/          ← Data pipeline scripts
│   │   ├── scraper.py    ← YouTube transcript downloader
│   │   ├── embed.js      ← Node.js embedding via @xenova/transformers
│   │   ├── seed_kb.py    ← Pattern seeding
│   │   └── calibrate_20.py ← Confidence gate calibration
│   ├── kb/               ← Pattern knowledge base files
│   ├── start.sh / stop.sh
│   └── package.json      ← Node deps for embedding
├── deck/                 ← open-slide presentation
│   ├── slides/           ← Slide source files (React TSX)
│   │   ├── value-prop/   ← Value proposition deck
│   │   ├── architecture/ ← System architecture deck
│   │   ├── search-pipeline/ ← Search pipeline deck
│   │   └── patterns-system/ ← Patterns & dashboard deck
│   ├── themes/           ← Custom slide themes
│   ├── AGENTS.md         ← open-slide authoring guide
│   └── README.md
├── AGENTS.md             ← THIS FILE — AI onboarding guide
├── CLAUDE.md → AGENTS.md
├── README.md
└── .gitignore
```

## System Architecture (4 Layers)

```
YouTube (2,502 videos)
    ↓ scraper (youtube-transcript-api)
┌──────────────────────────────┐
│ Layer 1: Data Ingestion      │
│ SQLite DB: 17,286 chunks     │
│ FTS5 full-text search index  │
└──────────────┬───────────────┘
    ↓ multilingual-e5-small (384-dim embeddings)
┌──────────────────────────────┐
│ Layer 2: Embedding Pipeline  │
│ 132MB vector index           │
│ Node.js via @xenova/transformers │
└──────────────┬───────────────┘
    ↓ cosine similarity + FTS5 fallback
┌──────────────────────────────┐
│ Layer 3: Search Engine       │
│ Semantic (primary)           │
│ FTS5 keyword (fallback)      │
│ All patterns (last resort)   │
│ Confidence gate: 0.84        │
└──────────────┬───────────────┘
    ↓ patterns + chunks + market data
┌──────────────────────────────┐
│ Layer 4: Application Layer   │
│ Streamlit dashboard :8501    │
│ yfinance live data           │
│ DeepSeek v4 Pro AI reasoning │
│ Audit trail (SQLite)         │
└──────────────────────────────┘
```

## Database Schema

File: `app/data/micha.db` (142MB — **gitignored**)

### Core Tables

| Table | Rows | Purpose |
|-------|------|---------|
| `videos` | 2,502 | YouTube video metadata |
| `transcript_chunks` | 17,306 | Transcript text with FTS5 index |
| `chunks_fts` | virtual | FTS5 index over transcript_chunks |
| `reasoning_patterns` | 20 | Micha's trading patterns |
| `patterns_fts` | virtual | FTS5 index over patterns |
| `scraper_state` | 2,502 | Download status per video |
| `recommendation_audit` | varies | Audit trail of AI decisions |

### reasoning_patterns columns

```sql
id, video_id, pattern_type, trigger_context, reasoning,
confidence_signal ('bullish'|'bearish'|'neutral'|'conditional'),
conditions, source_quote, video_title, chunk_id
```

### recommendation_audit columns

```sql
id, timestamp, query, ticker, recommendation,
confidence_pct, patterns_used (JSON), market_data_snapshot (JSON),
ai_raw_output (JSON)
```

## Pattern System

- **20 patterns** extracted from Micha's YouTube content
- **Semantic search**: multilingual-e5-small 384-dim embeddings → cosine similarity
- **Confidence gate**: 0.84 (calibrated against 20 test queries)
  - ≥0.84: Strong match, 14/20 queries return avg 8 chunks
  - 0.78-0.84: Moderate match
  - <0.78: Low match, may still be relevant
- **Fallback chain**: Semantic → FTS5 keyword → All patterns (guaranteed results)
- **Signals**: bullish 🟢, conditional 🟡, neutral ⚪, bearish 🔴

## Dashboard Display Modes

| Feature | Basic | Pro |
|---------|-------|-----|
| Decision Matrix (BUY/HOLD/WAIT/AVOID) | ✅ | ✅ |
| Recommendation card | ✅ | ✅ |
| Confidence meter | ✅ | ✅ |
| Pattern signal pie | ✅ | ✅ |
| Key numbers | ✅ | ✅ |
| Reasoning chain | ✅ | ✅ |
| KB citations | ✅ | ✅ |
| Market snapshot with gauges | — | ✅ |
| 52-week range gauge | — | ✅ |
| PE valuation gauge | — | ✅ |
| Volume chart | — | ✅ |
| Financial health bars | — | ✅ |
| Sector peer comparison | — | ✅ |
| Pattern activation heatmap | — | ✅ |
| Pattern score chart | — | ✅ |
| Audit trail history | — | ✅ |

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Dashboard framework | Streamlit |
| Charts | Plotly + Plotly Express |
| Market data | yfinance |
| AI reasoning | DeepSeek v4 Pro (OpenCode Go API) |
| Embedding model | multilingual-e5-small (384-dim) |
| Embedding runtime | Node.js + @xenova/transformers |
| Database | SQLite with FTS5 |
| Slides framework | open-slide (React TSX) |
| Public access | Tailscale Funnel |

## Credentials Needed

| Env Variable | Purpose |
|-------------|---------|
| `OPENCODE_GO_API_KEY` | DeepSeek AI reasoning (OpenCode Go plan) |

Without the API key, the dashboard uses a rule-based fallback analysis.

## Model Routing (OpenCode Go Plan)

| Model | Req/5h | When to use |
|-------|--------|-------------|
| deepseek-v4-flash | 31,650 | Default workhorse |
| deepseek-v4-pro | 3,450 | Hard reasoning, financial analysis |
| minimax-m2.7 | 3,400 | Simple tasks, DB queries |
| qwen3.5-plus | 10,200 | Hebrew, vision tasks |

**Rule**: V4 Flash first for everything. Escalate to V4 Pro only if results are poor.
Simple/routine tasks → MiniMax M2.7 to conserve V4 Flash allocation.

## Conventions

- **Python**: f-strings, type hints, snake_case
- **Streamlit**: functions for each render component, session_state for persistence
- **Slides**: Each slide is `deck/slides/<id>/index.tsx` — pure React inline styles
- **No dependencies added without review** — keep the stack lean
- **Commit messages**: Conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`)

## Live URLs

| Service | URL |
|---------|-----|
| Dashboard (public) | https://nuc-server.tail8cfaa2.ts.net |
| Database browser | https://nuc-server.tail8cfaa2.ts.net/db/ |
| Dashboard (LAN) | http://192.168.1.214:8501 |
| Slide deck (LAN) | http://192.168.1.214:5175 |

## Pitfalls

- **The 142MB SQLite DB is gitignored** — a fresh clone needs `data/micha.db` restored from backup or re-scraped
- **Node.js required for embeddings** — semantic search won't work without it
- **yfinance can be unstable** for some international tickers
- **Rate limits**: OpenCode Go plan has per-model req/5h limits (see table above)
- **FTS5 requires specific SQLite build** — standard Python sqlite3 includes it

## Agent Handoff & Journey Logging

Every AI agent working on this repo **MUST** follow these rules. They ensure no agent starts without context, and every action is traceable.

### The Rule: Read JOURNEY.md, Write to JOURNEY.md

There is one file that tracks all agent activity: **`JOURNEY.md`** at the repo root.

- **On start** — read the last 10 entries of `JOURNEY.md` for recent context
- **Before working** — write a 🟢 `START` entry declaring what you're doing and why
- **During work** — write ⚡ `EXECUTE` entries at each milestone (files changed, decisions made)
- **If stuck** — write 🔴 `BLOCKED` with the issue and resolution
- **On handoff** — write 🔄 `HANDOFF` with explicit current state + next steps for the receiver
- **On completion** — write ✅ `DONE` with summary and verification

### Entry Format

```markdown
## #NNN PHASE — 2026-05-14 HH:MM UTC
**Agent:** Name (model) · **Flow:** `tag`
**Task:** One-line summary
```
• What you did → file or outcome
• Each bullet is one action
```
**Next:** What should happen next (required for HANDOFF/DONE)
```

See `JOURNEY.md` header for the full legend of phases (🟢⚡🔄🔴 etc.) and flow tags (`smooth`, `rework`, `bounced`, etc.).

### Self-Explanatory Design

`JOURNEY.md` teaches itself. Its header contains a complete reference:
- All phase emojis with their meanings
- All flow tags with what they signal (good ✅ or bad 🔴)
- The entry template

No external docs needed. Open the file and you instantly understand the system.

### Flow Tags Reveal Bad Workflows

When you scan `JOURNEY.md`, watch for these tags:

| Tag | Problem it signals |
|-----|-------------------|
| `rework` | Context was lost — agent didn't know something was already done |
| `bounced` | Unnecessary A→B→A agent ping-pong — workflow needs restructuring |
| `confused` | Task wasn't defined clearly enough before work started |
| `overhead` | Task was too big — should have been split into smaller steps |
| `blocked` | Pre-flight checks were missed — dependency wasn't verified upfront |
