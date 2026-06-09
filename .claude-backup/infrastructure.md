# Infrastructure — Micha Stocks

## Overview

All services run on an Intel NUC home server exposed via Tailscale Funnel.
No cloud hosting. No Vercel. No Docker (runs natively on the NUC).

## Services

### Streamlit Dashboard (port 8501)
- **What:** Main application — AI-powered stock analysis UI
- **Where:** Intel NUC at 192.168.1.214
- **Run:** `cd /home/nuc/micha-stocks/app && streamlit run streamlit_app/app.py --server.port 8501 --server.address 0.0.0.0`
- **Process manager:** pm2 (or systemd)
- **Public URL:** https://nuc-server.tail8cfaa2.ts.net (via Tailscale Funnel)

### SQLite Database
- **File:** `app/data/micha.db` (142MB — gitignored)
- **Contains:** 2,502 YouTube videos, 17,286 transcript chunks, 20 reasoning patterns, FTS5 index, audit trail
- **Backup:** Manual. Must restore from backup or re-scrape after a format.

### Node.js Embedding Service
- **What:** Generates 384-dim embeddings using multilingual-e5-small via @xenova/transformers
- **Why needed:** Python cannot run this model directly — Node.js handles it
- **Run:** `cd app && node scripts/embed.js`
- **Required for:** Semantic search (cosine similarity). Without it, falls back to FTS5 keyword search.

### Datasette (database browser, port 8001)
- **What:** Read-only web UI for browsing the SQLite database
- **Public URL:** https://nuc-server.tail8cfaa2.ts.net/db/
- **Run:** `datasette serve app/data/micha.db --port 8001`

### open-slide Deck (port 5175)
- **What:** React presentation about the project architecture
- **Where:** `deck/` directory
- **Run:** `cd deck && pnpm dev`
- **Public URL:** http://192.168.1.214:5175 (LAN only, not funnel-exposed)

## Tailscale Setup

- Tailscale installed on NUC: `tailscale up`
- Funnel enabled: `tailscale funnel 8501` (dashboard) and `tailscale funnel 8001` (Datasette)
- Machine name: `nuc-server` → resolves to `nuc-server.tail8cfaa2.ts.net`

## MCP Servers (Claude Code integration)

| Server | Purpose | Config |
|---|---|---|
| `linkedin-browser` | LinkedIn job/people search for Claude Code | uv run from `/mnt/c/Users/korm8/linkedin-mcp-server` |
| `figma` | Figma Dev Mode for design references | npx figma-developer-mcp with FIGMA_API_KEY |

## Data Pipeline

To rebuild the database from scratch:
1. `python app/scripts/scraper.py` — download transcripts (2,500+ videos, takes hours)
2. `node app/scripts/embed.js` — generate embeddings (hours)
3. `python app/scripts/seed_kb.py` — seed the 20 reasoning patterns
4. `python app/scripts/calibrate_20.py` — calibrate confidence gate (target: 0.84)
