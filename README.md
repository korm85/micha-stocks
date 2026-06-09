# Micha Stocks

> 2,500 hours of expert analysis. One question. An answer in 30 seconds — built by a PM, no data team needed.

Most retail investors drown in content or pay for subscriptions that recycle headlines. This tool extracted 20 repeatable trading patterns from 2,502 YouTube videos, indexed them semantically, and wires them to live market data — so any question about any ticker returns a sourced, reasoned signal instead of a guess.

---

## What it does

```
YouTube Channel (2,502 videos)
         │
         ▼
  Download transcripts
  17,286 chunks in SQLite
         │
         ▼
  Generate embeddings
  multilingual-e5-small
  384-dim vector index
         │
         ▼
  User asks: "Should I buy NVDA?"
         │
    ┌────┴────────────────────┐
    │  Semantic search        │
    │  Cosine similarity      │
    │  Confidence gate: 0.84  │
    └────┬────────────────────┘
         │ top matching patterns + chunks
         ▼
  DeepSeek v4 Pro reasons over:
  • 20 trading patterns
  • Live market data (yfinance)
  • PE, volume, 52-week range
         │
         ▼
  ┌──────────────────────────┐
  │  BUY / HOLD / WAIT / AVOID │
  │  + confidence score       │
  │  + sourced reasoning      │
  └──────────────────────────┘
```

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│                Intel NUC (home server)            │
│                                                  │
│  ┌─────────────────────────────────────────────┐ │
│  │ Streamlit Dashboard :8501                   │ │
│  │                                             │ │
│  │  Layer 1: Data Ingestion                    │ │
│  │  SQLite DB (142MB)                          │ │
│  │  17,286 transcript chunks · FTS5 index      │ │
│  │                  │                          │ │
│  │  Layer 2: Embedding Pipeline                │ │
│  │  Node.js + @xenova/transformers             │ │
│  │  384-dim vector index (132MB)               │ │
│  │                  │                          │ │
│  │  Layer 3: Search Engine                     │ │
│  │  Semantic (primary) → FTS5 → All patterns   │ │
│  │                  │                          │ │
│  │  Layer 4: Application                       │ │
│  │  yfinance live data · DeepSeek AI · Audit   │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  Datasette DB Browser :8001                      │
│  open-slide Deck      :5175                      │
└──────────────────────────────────────────────────┘
         │
         │ Tailscale Funnel (HTTPS)
         ▼
  https://nuc-server.tail8cfaa2.ts.net
  (publicly accessible, no port forwarding)
```

---

## Stack

| Layer | Tech |
|---|---|
| Dashboard | Streamlit |
| Charts | Plotly + Plotly Express |
| Market data | yfinance |
| AI reasoning | DeepSeek v4 Pro via OpenCode Go |
| Embedding model | multilingual-e5-small (384-dim) |
| Embedding runtime | Node.js + @xenova/transformers |
| Database | SQLite with FTS5 |
| Presentation | open-slide (React TSX) |
| Public access | Tailscale Funnel |

---

## Key features

- **Pattern-grounded signals** — BUY / HOLD / WAIT / AVOID backed by 20 sourced trading patterns
- **Semantic search** — finds relevant patterns by meaning, not just keywords (cosine similarity, confidence gate 0.84)
- **Live market data** — PE ratio, volume, 52-week range, analyst targets from yfinance
- **Two display modes** — Basic (bottom-line signals) and Pro (full expert dashboard with gauges, heatmaps, peer comparison)
- **Full audit trail** — every recommendation logged with patterns used, market snapshot, and AI output
- **Source-verified** — every pattern links to the exact video and chunk it came from

---

## Live demo

| Service | URL |
|---|---|
| Dashboard | https://nuc-server.tail8cfaa2.ts.net |
| Database browser | https://nuc-server.tail8cfaa2.ts.net/db/ |
| Slide deck (LAN) | http://192.168.1.214:5175 |

---

## Quick start

```bash
git clone git@github.com:korm85/micha-stocks
cd micha-stocks/app
pip install streamlit plotly yfinance requests pandas
streamlit run streamlit_app/app.py --server.port 8501 --server.address 0.0.0.0
```

**Note:** The SQLite database (142MB) is gitignored. You need `app/data/micha.db` from backup to run the app. See [RESTORE.md](./RESTORE.md) for full setup instructions.

---

## Restoring this setup

See [RESTORE.md](./RESTORE.md) — complete step-by-step guide an AI agent can follow to rebuild the full environment.

See [`.claude-backup/`](./.claude-backup/) for Claude Code config, hooks, memory, and infrastructure docs.

---

## Environment variables

| Variable | Purpose |
|---|---|
| `OPENCODE_GO_API_KEY` | DeepSeek AI reasoning via OpenCode Go plan |

See [`.claude-backup/env-vars.md`](./.claude-backup/env-vars.md) for full details.
