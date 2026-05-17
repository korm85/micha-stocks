#!/usr/bin/env bash
PORT="${1:-8501}"
PID=$(lsof -ti :$PORT 2>/dev/null)
if [ -n "$PID" ]; then
    kill $PID
    echo "🛑 Stopped app on port $PORT (PID: $PID)"
else
    echo "📡 No app running on port $PORT"
fi
