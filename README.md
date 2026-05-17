# Micha Stocks

AI-powered stock decision tool that applies Micha's reasoning framework from 2,500+ YouTube videos. Get actionable trade signals backed by sourced patterns and live market data.

## What it does

- **Ask any stock question** — "Should I buy NVDA?" or "Is my portfolio at risk?"
- **Two display modes** — Basic (bottom-line signals) or Pro (full expert dashboard)
- **Pattern-based AI** — reasoning grounded in 20 sourced trading patterns from Micha's content
- **Live market data** — yfinance feeds real-time prices, PE, volume, analyst targets
- **Source-verified** — every pattern links to the actual video + chunk it came from
- **Full audit trail** — every recommendation logged with patterns used and market snapshot

## Quick Start

```bash
git clone https://github.com/korm85/micha-stocks
cd micha-stocks

# Dashboard
cd app
pip install streamlit plotly yfinance requests pandas
streamlit run streamlit_app/app.py

# Slide deck
cd deck
pnpm install
pnpm dev
```

See [AGENTS.md](./AGENTS.md) for the complete architecture, DB schema, and AI agent onboarding.

## Live Demo

| Service | URL |
|---------|-----|
| **Dashboard** | https://nuc-server.tail8cfaa2.ts.net |
| **Database Browser** | https://nuc-server.tail8cfaa2.ts.net/db/ |
| **Slide Deck** | http://192.168.1.214:5175 |

## Architecture (4 Layers)

1. **Data Ingestion** — Scraper downloads 2,502 YouTube transcripts → 17,286 chunks in SQLite + FTS5
2. **Embedding Pipeline** — multilingual-e5-small generates 384-dim vectors for every chunk and pattern
3. **Search Engine** — Semantic search (cosine similarity) → FTS5 keyword → All patterns fallback
4. **Application Layer** — Streamlit dashboard + yfinance + DeepSeek AI reasoning + audit trail

## Tech Stack

Streamlit · Plotly · yfinance · DeepSeek v4 Pro · SQLite FTS5 · open-slide · Tailscale Funnel
