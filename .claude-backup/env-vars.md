# Required Environment Variables — Micha Stocks

## Runtime (set in shell or systemd unit)

| Variable | Purpose |
|---|---|
| `OPENCODE_GO_API_KEY` | DeepSeek AI reasoning via OpenCode Go API. Used in `app/streamlit_app/app.py` for AI recommendations. Without it, dashboard falls back to rule-based analysis. |

## Infrastructure (no env var needed — uses Tailscale)

The dashboard runs on the NUC and is exposed publicly via Tailscale Funnel.
No cloud hosting credentials required. Tailscale auth is managed via `tailscale up` on the NUC.

## How to get values

- `OPENCODE_GO_API_KEY` — log into https://opencode.ai, go to API keys section. Uses the "Go" plan.
