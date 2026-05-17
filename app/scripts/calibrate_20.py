#!/usr/bin/env python3.14
"""
Calibrate search accuracy with the new 20-pattern KB.
Loads pre-computed embeddings from pattern_embeddings.json,
embeds queries via embed.js, and evaluates against the
20-query calibration test set.

Previous baseline (12 patterns): 65% Top-1, 90% Top-5
"""
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
PATTERN_EMBEDDINGS_PATH = BASE_DIR / "data" / "pattern_embeddings.json"
CALIBRATION_PATH = BASE_DIR / "calibration_test_set.json"
EMBED_SCRIPT = BASE_DIR / "scripts" / "embed.js"

# Pattern ID ranges
OLD_PATTERN_IDS = {11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22}
NEW_PATTERN_IDS = {23, 24, 25, 26, 27, 28, 29, 30}


# ── Math helpers ────────────────────────────────────────────────────

def normalize(v):
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v] if norm > 0 else v


def cosine_sim(a, b):
    return sum(x * y for x, y in zip(a, b))


# ── Data loading ────────────────────────────────────────────────────

def load_pattern_embeddings():
    """Load pre-computed pattern embeddings from JSON."""
    with open(PATTERN_EMBEDDINGS_PATH) as f:
        raw = json.load(f)

    pattern_map = {}
    vecs = {}
    for pid_str, item in raw.items():
        pid = int(pid_str)
        emb = item["embedding"]
        vecs[pid] = normalize(emb)
        pattern_map[pid] = {
            "pattern_type": item["pattern_type"],
            "is_new": pid in NEW_PATTERN_IDS,
        }
    return pattern_map, vecs


def load_calibration():
    with open(CALIBRATION_PATH) as f:
        calib = json.load(f)
    return calib["tests"]


def embed_queries(queries):
    """Embed a list of {id, text} query objects using embed.js."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(queries, f)
        tmp_input = f.name

    tmp_output = "/tmp/calibrate20_query_embeddings.json"

    cmd = ["node", str(EMBED_SCRIPT), tmp_input, tmp_output, "--query"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    finally:
        if os.path.exists(tmp_input):
            os.unlink(tmp_input)

    if result.returncode != 0:
        print(f"  ❌ Embedding failed:\n  {result.stderr[:500]}", file=sys.stderr)
        sys.exit(1)

    with open(tmp_output) as f:
        qry_embeds = json.load(f)
    if os.path.exists(tmp_output):
        os.unlink(tmp_output)

    qry_vecs = {}
    for item in qry_embeds:
        qry_vecs[item["id"]] = normalize(item["embedding"])
    return qry_vecs


# ── Main ────────────────────────────────────────────────────────────

def run_calibration():
    print("=" * 78)
    print("  📐 CALIBRATION REPORT — 20-Pattern Knowledge Base")
    print("=" * 78)

    # ── 1. Load data ────────────────────────────────────────────────
    pattern_map, pat_vecs = load_pattern_embeddings()
    tests = load_calibration()

    pattern_ids = sorted(pat_vecs.keys())
    old_ids = sorted(pid for pid in pattern_ids if pid in OLD_PATTERN_IDS)
    new_ids = sorted(pid for pid in pattern_ids if pid in NEW_PATTERN_IDS)

    print(f"\n📦 Pattern embeddings loaded: {len(pat_vecs)} total")
    print(f"   Old patterns (1–12): {len(old_ids)}")
    for pid in old_ids:
        print(f"      ID {pid:2d}: {pattern_map[pid]['pattern_type']}")
    print(f"   New patterns (13–20): {len(new_ids)}")
    for pid in new_ids:
        print(f"      ID {pid:2d}: {pattern_map[pid]['pattern_type']}")

    print(f"\n📋 Calibration test set: {len(tests)} queries")

    # Build type → id mapping
    type_to_id = {}
    for pid, info in pattern_map.items():
        type_to_id[info["pattern_type"]] = pid

    # ── 2. Embed queries ────────────────────────────────────────────
    print(f"\n⏳ Embedding {len(tests)} queries with embed.js...")
    queries_for_embed = [{"id": qi, "text": t["query"]} for qi, t in enumerate(tests)]
    qry_vecs = embed_queries(queries_for_embed)
    print(f"   ✅ Queries embedded: {len(qry_vecs)}")

    # ── 3. Evaluate ─────────────────────────────────────────────────
    top1_correct = 0
    top3_correct = 0
    top5_correct = 0
    total_queries = len(tests)
    query_details = []

    # Confusion counters
    new_as_top1_for_old = {pid: 0 for pid in new_ids}   # new pattern #1 when old-pattern query
    old_as_top1_for_new = {pid: 0 for pid in old_ids}   # old pattern #1 when new-pattern query

    for qi, test in enumerate(tests):
        qvec = qry_vecs[qi]
        ground_truth_types = set(test["ground_truth_patterns"])
        ground_truth_ids = set()
        for gt_type in ground_truth_types:
            if gt_type in type_to_id:
                ground_truth_ids.add(type_to_id[gt_type])

        # Score all patterns against this query
        scored = []
        for pid in pattern_ids:
            score = cosine_sim(qvec, pat_vecs[pid])
            scored.append((score, pid, pattern_map[pid]["pattern_type"]))

        scored.sort(reverse=True)  # highest first

        top1_score, top1_pid, top1_type = scored[0]
        top3_pids = {scored[i][1] for i in range(3)}
        top5_pids = {scored[i][1] for i in range(5)}
        top5_types = [scored[i][2] for i in range(5)]
        top5_scores = [round(scored[i][0], 4) for i in range(5)]

        # Top-1 check
        top1_ok = top1_pid in ground_truth_ids
        # Top-3 check
        top3_ok = bool(ground_truth_ids & top3_pids)
        # Top-5 check
        top5_ok = bool(ground_truth_ids & top5_pids)

        if top1_ok:
            top1_correct += 1
        if top3_ok:
            top3_correct += 1
        if top5_ok:
            top5_correct += 1

        # Find the top-scoring INCORRECT pattern
        top_incorrect = None
        for score, pid, ptype in scored:
            if pid not in ground_truth_ids:
                top_incorrect = {"type": ptype, "score": round(score, 4)}
                break

        # Collect correct pattern positions and scores
        correct_info = []
        for rank, (score, pid, ptype) in enumerate(scored, start=1):
            if pid in ground_truth_ids:
                correct_info.append({
                    "pid": pid,
                    "type": ptype,
                    "rank": rank,
                    "score": round(score, 4),
                    "is_new": pid in NEW_PATTERN_IDS,
                })

        # Track confusion
        has_old_gt = any(pid in OLD_PATTERN_IDS for pid in ground_truth_ids)
        has_new_gt = any(pid in NEW_PATTERN_IDS for pid in ground_truth_ids)

        if has_old_gt and top1_pid in NEW_PATTERN_IDS:
            new_as_top1_for_old[top1_pid] += 1
        if has_new_gt and top1_pid in OLD_PATTERN_IDS:
            old_as_top1_for_new[top1_pid] += 1

        query_details.append({
            "query": test["query"],
            "ground_truth": sorted(ground_truth_types),
            "top1": top1_type,
            "top1_ok": top1_ok,
            "top1_score": round(top1_score, 4),
            "top3_types": [scored[i][2] for i in range(3)],
            "top3_ok": top3_ok,
            "top5_types": top5_types,
            "top5_ok": top5_ok,
            "top5_scores": top5_scores,
            "correct_info": correct_info,
            "top_incorrect": top_incorrect,
        })

    top1_acc = top1_correct / total_queries * 100
    top3_acc = top3_correct / total_queries * 100
    top5_acc = top5_correct / total_queries * 100

    # ── 4. Print overall results ─────────────────────────────────────
    print(f"\n{'=' * 78}")
    print(f"  📊 OVERALL ACCURACY")
    print(f"{'=' * 78}")
    print(f"  Top-1 Accuracy:  {top1_correct}/{total_queries} = {top1_acc:.1f}%")
    print(f"  Top-3 Accuracy:  {top3_correct}/{total_queries} = {top3_acc:.1f}%")
    print(f"  Top-5 Accuracy:  {top5_correct}/{total_queries} = {top5_acc:.1f}%")

    # Previous baseline
    PREV_TOP1 = 65.0
    PREV_TOP5 = 90.0

    print(f"\n{'─' * 78}")
    print(f"  📈 COMPARISON TO PREVIOUS BASELINE (12 patterns)")
    print(f"{'─' * 78}")
    print(f"  {'Metric':<30} {'Previous (12)':>15} {'Current (20)':>15} {'Δ':>10}")
    print(f"  {'─' * 72}")
    delta_t1 = top1_acc - PREV_TOP1
    delta_t5 = top5_acc - PREV_TOP5
    print(f"  {'Top-1 Accuracy':<30} {f'{PREV_TOP1:.1f}%':>15} {f'{top1_acc:.1f}%':>15} {delta_t1:>+8.1f}%")
    print(f"  {'Top-5 Accuracy':<30} {f'{PREV_TOP5:.1f}%':>15} {f'{top5_acc:.1f}%':>15} {delta_t5:>+8.1f}%")

    # ── 5. Per-query breakdown ───────────────────────────────────────
    print(f"\n{'─' * 78}")
    print(f"  📋 PER-QUERY BREAKDOWN")
    print(f"{'─' * 78}")

    for qi, d in enumerate(query_details):
        mark1 = "✅" if d["top1_ok"] else "❌"
        mark3 = "✅" if d["top3_ok"] else "❌"
        mark5 = "✅" if d["top5_ok"] else "❌"
        print(f"\n  Q{qi + 1:2d}: \"{d['query']}\"")
        print(f"       Ground truth: {', '.join(d['ground_truth'])}")
        print(f"       T1:{mark1} T3:{mark3} T5:{mark5}  Top-1: {d['top1']:30s} (score: {d['top1_score']:.4f})")
        print(f"       Top-3:  {' › '.join(d['top3_types'])}")
        print(f"       Top-5:  {' › '.join(d['top5_types'])}")
        print(f"       Scores: {d['top5_scores']}")

        if not d["top1_ok"]:
            print(f"       🥇 Top incorrect: {d['top_incorrect']['type']} ({d['top_incorrect']['score']:.4f})")

        for ci in d["correct_info"]:
            badge = "🆕" if ci["is_new"] else ""
            print(f"       {badge} Correct \"{ci['type']}\" → rank #{ci['rank']} (score: {ci['score']:.4f})")

    # ── 6. Confusion analysis ────────────────────────────────────────
    print(f"\n{'=' * 78}")
    print(f"  🔀 CONFUSION ANALYSIS: New vs Old Patterns")
    print(f"{'=' * 78}")

    print(f"\n  🆕 New patterns appearing as Top-1 when old-pattern query was expected:")
    any_found = False
    for npid in new_ids:
        cnt = new_as_top1_for_old[npid]
        if cnt > 0:
            any_found = True
            print(f"     ID {npid:2d} ({pattern_map[npid]['pattern_type']:35s}) → {cnt} time(s)")
    if not any_found:
        print(f"     (none — new patterns never outranked correct old patterns at Top-1)")

    print(f"\n  🗓️  Old patterns appearing as Top-1 when new-pattern query was expected:")
    any_found = False
    for opid in old_ids:
        cnt = old_as_top1_for_new[opid]
        if cnt > 0:
            any_found = True
            print(f"     ID {opid:2d} ({pattern_map[opid]['pattern_type']:35s}) → {cnt} time(s)")
    if not any_found:
        print(f"     (none — old patterns never outranked correct new patterns at Top-1)")

    # Top-5 level confusion
    new_in_old_top5 = {pid: 0 for pid in new_ids}
    old_in_new_top5 = {pid: 0 for pid in old_ids}
    new_in_new_top5 = {pid: 0 for pid in new_ids}

    for qi, test in enumerate(tests):
        qvec = qry_vecs[qi]
        gt_types = set(test["ground_truth_patterns"])
        gt_ids = set(type_to_id[t] for t in gt_types if t in type_to_id)
        has_old_gt = any(pid in OLD_PATTERN_IDS for pid in gt_ids)
        has_new_gt = any(pid in NEW_PATTERN_IDS for pid in gt_ids)

        scored = sorted([(cosine_sim(qvec, pat_vecs[pid]), pid) for pid in pattern_ids], reverse=True)
        top5_pids = {scored[i][1] for i in range(5)}

        for pid in top5_pids:
            if has_old_gt and pid in NEW_PATTERN_IDS:
                new_in_old_top5[pid] += 1
            if has_new_gt and pid in OLD_PATTERN_IDS:
                old_in_new_top5[pid] += 1
            if has_new_gt and pid in NEW_PATTERN_IDS:
                new_in_new_top5[pid] += 1

    print(f"\n  📊 Top-5 confusion: New patterns appearing in old-pattern query results:")
    any_found = False
    for npid, cnt in sorted(new_in_old_top5.items(), key=lambda x: -x[1]):
        if cnt > 0:
            any_found = True
            print(f"     {pattern_map[npid]['pattern_type']:35s} → in Top-5 of {cnt} old-pattern query(ies)")
    if not any_found:
        print(f"     (none)")

    print(f"\n  📊 Top-5 confusion: Old patterns appearing in new-pattern query results:")
    any_found = False
    for opid, cnt in sorted(old_in_new_top5.items(), key=lambda x: -x[1]):
        if cnt > 0:
            any_found = True
            print(f"     {pattern_map[opid]['pattern_type']:35s} → in Top-5 of {cnt} new-pattern query(ies)")
    if not any_found:
        print(f"     (none)")

    # ── 7. Summary ───────────────────────────────────────────────────
    print(f"\n{'=' * 78}")
    print(f"  ✅ SUMMARY")
    print(f"{'=' * 78}")
    print(f"  Calibration with 20 patterns:")
    print(f"    Top-1:  {top1_acc:.1f}%  ({top1_correct}/{total_queries})")
    print(f"    Top-3:  {top3_acc:.1f}%  ({top3_correct}/{total_queries})")
    print(f"    Top-5:  {top5_acc:.1f}%  ({top5_correct}/{total_queries})")
    print(f"  Previous baseline with 12 patterns:")
    print(f"    Top-1:  {PREV_TOP1:.1f}%")
    print(f"    Top-5:  {PREV_TOP5:.1f}%")

    print(f"\n  📊 Accuracy Δ vs previous baseline:")
    if delta_t1 >= 0:
        print(f"    Top-1:  +{delta_t1:.1f}% ✅")
    else:
        print(f"    Top-1:  {delta_t1:.1f}% ⚠️")
    if delta_t5 >= 0:
        print(f"    Top-5:  +{delta_t5:.1f}% ✅")
    else:
        print(f"    Top-5:  {delta_t5:.1f}% ⚠️")

    return {
        "top1_accuracy": top1_acc,
        "top3_accuracy": top3_acc,
        "top5_accuracy": top5_acc,
        "top1_correct": top1_correct,
        "top3_correct": top3_correct,
        "top5_correct": top5_correct,
        "total_queries": total_queries,
        "previous_top1": PREV_TOP1,
        "previous_top5": PREV_TOP5,
        "details": query_details,
    }


if __name__ == "__main__":
    run_calibration()
