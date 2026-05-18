#!/usr/bin/env bash
# Micha Stocks Deck server
set -e
DECK_DIR="$HOME/micha-stocks-deck/deck"
cd "$DECK_DIR"
# Kill existing if any
lsof -ti :8515 2>/dev/null | xargs kill 2>/dev/null || true
sleep 1
python3 serve_deck.py 8515 /deck/
