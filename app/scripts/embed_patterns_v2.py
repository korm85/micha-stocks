#!/usr/bin/env python3.14
"""
Regenerate pattern embeddings with enriched text that includes source_quote and video_title.
This should improve semantic discrimination since each pattern now has more distinctive content.
"""
import json, os, sqlite3, subprocess, sys, tempfile, math
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "micha.db"
EMBED_SCRIPT = BASE_DIR / "scripts" / "embed.js"
OUTPUT_PATH = BASE_DIR / "data" / "pattern_embeddings.json"

# ── Step 1: Load patterns with enriched text ───────────────────────

print("📦 Loading patterns from DB with source-linked data...")
conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
rows = conn.execute("""
    SELECT rp.id, rp.pattern_type, rp.reasoning, rp.trigger_context, 
           rp.conditions, rp.source_quote,
           COALESCE(v.title, 'Micha video') as video_title
    FROM reasoning_patterns rp
    LEFT JOIN videos v ON rp.video_id = v.id
    ORDER BY rp.id
""").fetchall()
conn.close()

print(f"   {len(rows)} patterns loaded")

# Build enriched text for each pattern
embed_input = []
for r in rows:
    # Construct a rich text that includes everything distinctive about this pattern
    text_parts = [
        f"Pattern: {r['pattern_type'].replace('_', ' ')}",
        f"Teaching: {r['reasoning'] or ''}",
        f"When to use: {r['trigger_context'] or ''}",
    ]
    conditions_val = r["conditions"] if r["conditions"] else None
    if conditions_val:
        text_parts.append(f"Conditions: {conditions_val}")
    
    source_val = r["source_quote"] if r["source_quote"] else None
    if source_val:
        quote_clean = source_val[:300].replace("\n", " ")
        text_parts.append(f"Micha says: {quote_clean}")
    
    title_val = r["video_title"] if r["video_title"] else None
    if title_val:
        text_parts.append(f"From video: {r['video_title']}")
    
    full_text = ". ".join(text_parts)
    embed_input.append({"id": r["id"], "text": full_text})

# Show what we're embedding
print("\nSample enriched texts:")
for item in embed_input[:3]:
    print(f"\n  ID {item['id']}: {item['text'][:200]}...")

# ── Step 2: Embed via Node.js ──────────────────────────────────────

with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    json.dump(embed_input, f)
    tmp_input = f.name

tmp_output = "/tmp/pattern_embeddings_v2_tmp.json"

print("\n🧠 Computing enriched pattern embeddings...")
result = subprocess.run(
    ["node", str(EMBED_SCRIPT), tmp_input, tmp_output],
    capture_output=True, text=True, timeout=300
)
os.unlink(tmp_input)

if result.returncode != 0:
    print(f"❌ Embedding failed: {result.stderr[:500]}")
    sys.exit(1)

# ── Step 3: Save new embeddings ────────────────────────────────────

with open(tmp_output) as f:
    pattern_data = json.load(f)
os.unlink(tmp_output)

output = {}
for item in pattern_data:
    pid = item["id"]
    ptype = next(r["pattern_type"] for r in rows if r["id"] == pid)
    output[pid] = {
        "pattern_type": ptype,
        "embedding": item["embedding"],
        "text": next(r for r in embed_input if r["id"] == pid)["text"]
    }

# Backup old embeddings
old_path = BASE_DIR / "data" / "pattern_embeddings.json.bak"
if os.path.exists(str(OUTPUT_PATH)):
    os.rename(str(OUTPUT_PATH), str(old_path))
    print(f"📦 Backed up old embeddings to {old_path}")

with open(OUTPUT_PATH, "w") as f:
    json.dump(output, f, ensure_ascii=False)

print(f"✅ Saved {len(output)} enriched pattern embeddings to {OUTPUT_PATH}")
print(f"\n📊 Size comparison:")
print(f"   Old: {os.path.getsize(old_path):,} bytes")
print(f"   New: {os.path.getsize(OUTPUT_PATH):,} bytes")
