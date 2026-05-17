#!/usr/bin/env bash
# Micha Stocks — One-Click Launcher
# ===================================
# Start the Streamlit app with API key and show URL.
# Run: bash start.sh

set -e
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${1:-8501}"

echo "🚀 Starting Micha Stocks Dashboard..."
echo ""

# Load API key from environment
if [ -f "$HOME/.hermes/.env" ]; then
    set -a
    source "$HOME/.hermes/.env"
    set +a
fi

# Kill any existing Streamlit on this port
lsof -ti :$PORT 2>/dev/null | xargs kill 2>/dev/null || true
sleep 1

# Start Streamlit in background with API key
cd "$APP_DIR"
nohup env OPENCODE_GO_API_KEY="$OPENCODE_GO_API_KEY" \
    streamlit run streamlit_app/app.py \
    --server.address 0.0.0.0 \
    --server.port $PORT \
    --server.headless true \
    > /tmp/micha-app.log 2>&1 &

PID=$!
echo "📡 Server starting (PID: $PID)..."

# Wait for it to be ready
for i in $(seq 1 15); do
    sleep 1
    if curl -s -o /dev/null -w "" http://localhost:$PORT/ 2>/dev/null; then
        echo "✅ App is running!"
        echo ""
        echo "   ┌────────────────────────────────────────────────"
        echo "   │ 🌐 Open in your browser:"
        echo "   │"
        echo "   │   http://localhost:$PORT"
        HOST_IP=$(hostname -I | awk '{print $1}')
        if [ -n "$HOST_IP" ]; then
            echo "   │   http://$HOST_IP:$PORT"
        fi
        echo "   │"
        echo "   │   Type: Should I buy NVDA?"
        echo "   └────────────────────────────────────────────────"
        echo ""
        echo "📋 Logs: tail -f /tmp/micha-app.log"
        echo "🛑 Stop: kill $PID"
        exit 0
    fi
done

echo "⚠️ Timed out — check logs: tail -f /tmp/micha-app.log"
exit 1
