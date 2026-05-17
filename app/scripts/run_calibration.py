#!/usr/bin/env python3.14
"""
Pragmatic calibration: analyze embedding score distributions and 
find the optimal confidence gate for the dashboard scraper.
Tests: for each calibration query, find top chunks and score distribution.
"""
import json, math, os, subprocess, sqlite3, sys, tempfile
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "micha.db"
EMBEDDINGS_PATH = "/tmp/embeddings.json"
CALIBRATION_PATH = BASE_DIR / "calibration_test_set.json"
EMBED_SCRIPT = BASE_DIR / "scripts" / "embed.js"

# ── Step 1: Load data ──────────────────────────────────────────────

print("📦 Loading calibration test set...")
with open(CALIBRATION_PATH) as f:
    calib = json.load(f)
tests = calib["tests"]
print(f"   {len(tests)} test queries")

print(f"📦 Loading chunk embeddings from {EMBEDDINGS_PATH}...")
with open(EMBEDDINGS_PATH) as f:
    chunk_data = json.load(f)
print(f"   {len(chunk_data)} chunk vectors")

conn = sqlite3.connect(str(DB_PATH))
chunk_text = {}
for row in conn.execute("SELECT id, substr(text, 1, 200) as t FROM transcript_chunks"):
    chunk_text[str(row[0])] = row[1]
conn.close()

# ── Step 2: Compute query embeddings (batch) ───────────────────────

print("🧠 Computing query embeddings...")
queries = [t["query"] for t in tests]
query_input = [{"id": i, "text": q} for i, q in enumerate(queries)]

with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    json.dump(query_input, f)
    tmp_input = f.name

result = subprocess.run(
    ["node", str(EMBED_SCRIPT), tmp_input, "/tmp/calib_query_emb_v3.json"],
    capture_output=True, text=True, timeout=600
)
os.unlink(tmp_input)

if result.returncode != 0:
    print(f"❌ Error: {result.stderr[:300]}")
    sys.exit(1)

with open("/tmp/calib_query_emb_v3.json") as f:
    query_embeds = json.load(f)
os.unlink("/tmp/calib_query_emb_v3.json")

# ── Step 3: Similarity engine ──────────────────────────────────────

def normalize(v):
    norm = math.sqrt(sum(x*x for x in v))
    return [x/norm for x in v] if norm > 0 else v

def cosine_sim(a, b):
    return sum(x*y for x,y in zip(a,b))

# Normalize all
chunk_norm = {}
for item in chunk_data:
    chunk_norm[item["id"]] = normalize(item["embedding"])

query_norm = {}
for item in query_embeds:
    query_norm[item["id"]] = normalize(item["embedding"])

# ── Step 4: Score distribution analysis ────────────────────────────

print(f"\n{'═'*72}")
print("  📊 SCORE DISTRIBUTION PER QUERY (top 30 chunks)")
print(f"{'═'*72}")

all_scores = []
all_gap_scores = []  # scores of the "gap" between consecutive ranked chunks

for qi, test in enumerate(tests):
    qvec = query_norm[qi]
    scored = []
    for cid, nvec in chunk_norm.items():
        score = cosine_sim(qvec, nvec)
        scored.append((score, cid))
    
    scored.sort(reverse=True)
    top_scores = [s for s, _ in scored[:30]]
    all_scores.extend(top_scores)
    
    # Score gaps (drop-off between consecutive chunks)
    gaps = [top_scores[i] - top_scores[i+1] for i in range(len(top_scores)-1)]
    all_gap_scores.extend(gaps)
    
    # Show top 5 text previews
    print(f"\n  Query #{qi+1}: {test['query'][:55]}")
    print(f"  Score | Gap  | Chunk preview")
    print(f"  {'─'*55}")
    prev_score = None
    for rank, (score, cid) in enumerate(scored[:10]):
        gap = f"{score - prev_score:.4f}" if prev_score else "  -  "
        txt = chunk_text.get(str(cid), "?")[:80].replace("\n", " ")
        print(f"  {score:.4f} | {gap} | {txt}")
        prev_score = score

# ── Step 5: Gate calibration ───────────────────────────────────────

print(f"\n{'═'*72}")
print("  🔬 GATE CALIBRATION ANALYSIS")
print(f"{'═'*72}")

gates = [x/100 for x in range(50, 96, 2)]  # 0.50 to 0.94 step 0.02

for gate in gates:
    above = 0
    below = 0
    chunks_above = 0
    queries_with_results = 0
    
    for qi, test in enumerate(tests):
        qvec = query_norm[qi]
        scored = [(cosine_sim(qvec, nvec), cid) for cid, nvec in chunk_norm.items()]
        scored.sort(reverse=True)
        
        above_count = sum(1 for s, _ in scored if s >= gate)
        chunks_above += above_count
        
        if above_count > 0:
            queries_with_results += 1
            above += 1
        
        # Score of the top non-matching (the drop to first chunk below gate)
    
    avg_chunks = chunks_above / len(tests)
    
    # Score gap at this gate (average score of the chunk just above vs just below)
    gap_at_gate = 0
    for qi in range(len(tests)):
        qvec = query_norm[qi]
        scored = sorted([(cosine_sim(qvec, nvec), cid) for cid, nvec in chunk_norm.items()], reverse=True)
        above_gate = [s for s, _ in scored if s >= gate]
        below_gate = [s for s, _ in scored if s < gate]
        if above_gate and below_gate:
            gap_at_gate += above_gate[-1] - below_gate[0]
    gap_at_gate = gap_at_gate / len(tests) if len(tests) > 0 else 0
    
    print(f"  Gate {gate:.2f}  |  Qry>0={above:3d}/{len(tests):2d}  | Avg chunks={avg_chunks:6.1f}  | Gap={gap_at_gate:.4f}")

# ── Step 6: Recommend gate and show distribution stats ─────────────

print(f"\n{'═'*72}")
print("  📊 SCORE DISTRIBUTION SUMMARY")
print(f"{'═'*72}")

all_scores.sort(reverse=True)
total = len(all_scores)

# Percentiles
for pct in [100, 99, 98, 95, 90, 80, 70, 60, 50, 25, 10, 5, 1]:
    idx = int(total * (100 - pct) / 100)
    idx = max(0, min(total-1, idx))
    print(f"  Top {pct:3d}% percentile: {all_scores[idx]:.4f}")

# Gap distribution
print(f"\n  Average score gaps between consecutive chunks:")
for k in [1, 2, 3, 5, 10]:
    gaps_for_k = all_gap_scores[k-1::k]
    avg_gap = sum(gaps_for_k) / len(gaps_for_k) if gaps_for_k else 0
    print(f"    Gap after top {k:2d} results (avg): {avg_gap:.4f}")

# Big gaps (significant drop-offs)
big_gaps = sorted([(gap, qi, rank) for qi, test in enumerate(tests) 
                    for rank, gap in enumerate(all_gap_scores[qi*29:(qi+1)*29]) 
                    if gap > 0.02], reverse=True)
if big_gaps:
    print(f"\n  Notable drop-offs (> 0.02):")
    for gap, qi, rank in big_gaps[:10]:
        print(f"    Query #{qi+1}: rank {rank+1}→{rank+2}: drop of {gap:.4f}")

# ── Step 7: Recommend ──────────────────────────────────────────────

print(f"\n{'═'*72}")
print("  ✅ RECOMMENDATION")
print(f"{'═'*72}")

# Find gate where avg chunks = ~5 (reasonable number of results)
for gate in [x/100 for x in range(50, 96)]:
    chunks_above = 0
    queries_with = 0
    for qi in range(len(tests)):
        qvec = query_norm[qi]
        scored = sorted([(cosine_sim(qvec, nvec), cid) for cid, nvec in chunk_norm.items()], reverse=True)
        count = sum(1 for s, _ in scored if s >= gate)
        chunks_above += count
        if count > 0:
            queries_with += 1
    avg = chunks_above / len(tests)
    ratio = queries_with / len(tests)
    
    if avg <= 3 and ratio >= 0.7:
        print(f"\n  📌 Recommended confidence gate: {gate:.2f}")
        print(f"     → Average chunks per query: {avg:.1f}")
        print(f"     → Queries with results: {queries_with}/{len(tests)} ({ratio:.0%})")
        
        # Show sample scores at this gate
        print(f"\n  Sample results at gate {gate:.2f}:")
        for qi in range(min(5, len(tests))):
            qvec = query_norm[qi]
            scored = sorted([(cosine_sim(qvec, nvec), cid) for cid, nvec in chunk_norm.items()], reverse=True)
            above = [(s, c) for s, c in scored if s >= gate]
            if above:
                txt = chunk_text.get(str(above[0][1]), "")[:80]
                print(f"    #{qi+1}: top={above[0][0]:.4f}, chunks={len(above)}, text=\"{txt}...\"")
            else:
                print(f"    #{qi+1}: no results above gate")
        break

print(f"\n{'═'*72}")
