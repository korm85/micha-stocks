#!/usr/bin/env bash
# Micha Stocks Deck static server
# Serves built deck from dist/ on port 8515
# Tailscale Funnel strips /deck/ prefix before forwarding here
set -e
DECK_DIR="$HOME/micha-stocks-deck/deck"
DIST_DIR="$DECK_DIR/dist"
cd "$DECK_DIR"
# Kill existing if any
lsof -ti :8515 2>/dev/null | xargs kill 2>/dev/null || true
sleep 1
exec python3 -m http.server 8515 --directory "$DIST_DIR"
