#!/usr/bin/env python3.14
"""Test semantic search with embeddings."""
import json, math, sqlite3, sys

with open('/tmp/embeddings.json') as f:
    data = json.load(f)

conn = sqlite3.connect('/home/nuc/micha-stocks-app/data/micha.db')
chunk_text = dict(conn.execute('SELECT id, substr(text,1,200) FROM transcript_chunks').fetchall())
conn.close()

def normalize(v):
    norm = math.sqrt(sum(x*x for x in v))
    return [x/norm for x in v] if norm > 0 else v

def cosine_sim(a, b):
    return sum(x*y for x,y in zip(a,b))

# Simulate query by computing mean of top similar chunks to a concept
query_concept = "stop loss sell exit losing money trade"
# We cheat slightly: find chunks mentioning these keywords
keywords = ["stop loss", "למכור", "יציאה", "הפסד", "sell", "exit"]
hint_ids = set()
for item in data[:50]:  # Only check first 50 for speed
    tid = str(item['id'])
    text = chunk_text.get(tid, '').lower()
    if any(kw.lower() in text for kw in keywords):
        hint_ids.add(tid)

print(f"Found {len(hint_ids)} hint chunks about stop loss/selling")

# Get a query vector by averaging hint vectors
hint_vectors = []
for item in data:
    if str(item['id']) in hint_ids:
        hint_vectors.append(item['embedding'])

if hint_vectors:
    query_vec = normalize([sum(x)/len(hint_vectors) for x in zip(*hint_vectors)])
    
    # Score all chunks by cosine similarity
    scored = []
    for item in data:
        vec = normalize(item['embedding'])
        score = cosine_sim(query_vec, vec)
        scored.append((score, item['id']))
    
    scored.sort(reverse=True)
    
    print("\nTop 10 semantic matches for 'stop loss / selling':")
    print(f"{'Score':>8} | Chunk | Text")
    print("-"*70)
    for score, tid in scored[:10]:
        text = chunk_text.get(str(tid), '?')[:100]
        print(f"{score:.4f} | #{tid:<5} | {text}")
