#!/usr/bin/env python3.14
"""
Pre-compute pattern embeddings and store them for fast retrieval.
Run once after patterns are seeded.
"""
import json, os, sqlite3, subprocess, sys, tempfile, math
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "micha.db"
EMBED_SCRIPT = BASE_DIR / "scripts" / "embed.js"
OUTPUT_PATH = BASE_DIR / "data" / "pattern_embeddings.json"

# ── Step 1: Load patterns from DB ──────────────────────────────────

print("📦 Loading patterns from DB...")
conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT id, pattern_type, reasoning, trigger_context, conditions FROM reasoning_patterns"
).fetchall()
conn.close()

if not rows:
    print("❌ No patterns found in DB. Run seed_real_patterns.py first.")
    sys.exit(1)

print(f"   {len(rows)} patterns loaded")

# Build texts for embedding — combine all fields
embed_input = []
for r in rows:
    text_parts = [
        r["pattern_type"].replace("_", " "),
        r["reasoning"] or "",
        r["trigger_context"] or "",
    ]
    if r["conditions"]:
        text_parts.append(r["conditions"])
    full_text = " | ".join(text_parts)
    embed_input.append({"id": r["id"], "text": full_text})

# ── Step 2: Embed via Node.js ──────────────────────────────────────

with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    json.dump(embed_input, f)
    tmp_input = f.name

tmp_output = "/tmp/pattern_embeddings_tmp.json"

print("🧠 Computing pattern embeddings (batch via Node.js)...")
result = subprocess.run(
    ["node", str(EMBED_SCRIPT), tmp_input, tmp_output],
    capture_output=True, text=True, timeout=300
)
os.unlink(tmp_input)

if result.returncode != 0:
    print(f"❌ Embedding failed: {result.stderr[:500]}")
    sys.exit(1)

# ── Step 3: Save ───────────────────────────────────────────────────

with open(tmp_output) as f:
    pattern_data = json.load(f)
os.unlink(tmp_output)

# Build output: pattern_id -> {type, embedding}
output = {}
for item in pattern_data:
    pid = item["id"]
    ptype = next(r["pattern_type"] for r in rows if r["id"] == pid)
    output[pid] = {
        "pattern_type": ptype,
        "embedding": item["embedding"]
    }

with open(OUTPUT_PATH, "w") as f:
    json.dump(output, f, ensure_ascii=False)

print(f"✅ Saved {len(output)} pattern embeddings to {OUTPUT_PATH}")
