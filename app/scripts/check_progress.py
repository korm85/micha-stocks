#!/usr/bin/env python3.14
"""Watch Micha transcript downloads and report progress."""
import sqlite3, os, json

DB_PATH = os.path.expanduser("~/micha-stocks-app/data/micha.db")
STATUS_FILE = "/tmp/micha_download_status.json"

conn = sqlite3.connect(DB_PATH)
downloaded = conn.execute("SELECT COUNT(*) FROM scraper_state WHERE status='downloaded'").fetchone()[0]
failed = conn.execute("SELECT COUNT(*) FROM scraper_state WHERE status='failed'").fetchone()[0]
pending = conn.execute("SELECT COUNT(*) FROM scraper_state WHERE status='pending'").fetchone()[0]
total = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
chunks = conn.execute("SELECT COUNT(*) FROM transcript_chunks").fetchone()[0]
conn.close()

status = {
    "downloaded": downloaded,
    "failed": failed,
    "pending": pending,
    "total": total,
    "chunks": chunks,
    "pct": round(downloaded / total * 100, 1) if total > 0 else 0,
}

# Save for reference
with open(STATUS_FILE, "w") as f:
    json.dump(status, f)

# Human-readable summary
pct = status["pct"]
bar_len = 20
filled = int(bar_len * pct / 100)
bar = "█" * filled + "░" * (bar_len - filled)

print(f"📥 Micha Transcripts: {downloaded}/{total} ({pct}%)")
print(f"   {bar}")
print(f"   Chunks: {chunks} | Failed: {failed} | Pending: {pending}")
