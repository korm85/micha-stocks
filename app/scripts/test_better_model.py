#!/usr/bin/env python3.14
"""
Test better embedding models for pattern search.
Compares Top-1 and Top-5 accuracy across multiple models.
"""
import json
import math
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "micha.db"
EMBED_SCRIPT = BASE_DIR / "scripts" / "embed_better.js"
CALIBRATION_PATH = BASE_DIR / "calibration_test_set.json"
PATTERN_EMBEDDINGS_PATH = BASE_DIR / "data" / "pattern_embeddings.json"

# ── Models to test ──────────────────────────────────────────────────

MODELS = [
    {
        "name": "Xenova/multilingual-e5-small",
        "label": "multilingual-e5-small (BASELINE)",
        "dim": 384,
        "description": "Current model — multilingual, supports Hebrew+English",
    },
    {
        "name": "Xenova/bge-small-en-v1.5",
        "label": "bge-small-en-v1.5",
        "dim": 384,
        "description": "English optimized, better semantic matching, NO Hebrew support",
    },
    {
        "name": "Xenova/all-MiniLM-L6-v2",
        "label": "all-MiniLM-L6-v2",
        "dim": 384,
        "description": "Fast general purpose English model, NO Hebrew support",
    },
]

# ── Helpers ─────────────────────────────────────────────────────────

def normalize(v):
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v] if norm > 0 else v


def cosine_sim(a, b):
    return sum(x * y for x, y in zip(a, b))


def get_pattern_texts():
    """Get pattern texts from DB, same format as embed_patterns.py."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, pattern_type, reasoning, trigger_context, conditions FROM reasoning_patterns ORDER BY id"
    ).fetchall()
    conn.close()

    pattern_map = {}
    for r in rows:
        text_parts = [
            r["pattern_type"].replace("_", " "),
            r["reasoning"] or "",
            r["trigger_context"] or "",
        ]
        if r["conditions"]:
            text_parts.append(r["conditions"])
        full_text = " | ".join(text_parts)
        pattern_map[r["id"]] = {
            "pattern_type": r["pattern_type"],
            "text": full_text,
        }
    return pattern_map


def embed_texts(texts, model_name, is_query=False):
    """Embed a list of {id, text} objects using the specified model."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(texts, f)
        tmp_input = f.name

    tmp_output = f"/tmp/model_test_{model_name.split('/')[-1]}_{'q' if is_query else 'p'}.json"

    cmd = ["node", str(EMBED_SCRIPT), tmp_input, tmp_output, "--model", model_name]
    if is_query:
        cmd.append("--query")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600
        )
    finally:
        if os.path.exists(tmp_input):
            os.unlink(tmp_input)

    if result.returncode != 0:
        stderr = result.stderr[:500]
        raise RuntimeError(f"Embedding failed for {model_name}: {stderr}")

    with open(tmp_output) as f:
        data = json.load(f)
    if os.path.exists(tmp_output):
        os.unlink(tmp_output)

    return data


# ── Main Test ───────────────────────────────────────────────────────

def run_test():
    print("=" * 72)
    print("  🧪 EMBEDDING MODEL COMPARISON TEST")
    print("  Pattern Search: Top-1 / Top-5 Accuracy")
    print("=" * 72)

    # Load calibration tests
    with open(CALIBRATION_PATH) as f:
        calib = json.load(f)
    tests = calib["tests"]
    print(f"\n📋 Calibration test set: {len(tests)} queries")
    print(f"   12 patterns, 12 pattern types")

    # Get pattern texts
    pattern_map = get_pattern_texts()
    pattern_ids = sorted(pattern_map.keys())
    pattern_texts = [{"id": pid, "text": pattern_map[pid]["text"]} for pid in pattern_ids]
    print(f"\n📦 Patterns loaded: {len(pattern_texts)}")

    # For each test, build list of ground-truth pattern IDs
    # Map pattern_type -> pattern_id
    type_to_id = {}
    for pid, info in pattern_map.items():
        type_to_id[info["pattern_type"]] = pid

    all_results = {}

    for model_info in MODELS:
        model_name = model_info["name"]
        model_label = model_info["label"]
        print(f"\n{'─' * 72}")
        print(f"  🔍 Testing: {model_label}")
        print(f"     {model_info['description']}")
        print(f"{'─' * 72}")

        try:
            # Step 1: Embed patterns
            print(f"  ⏳ Embedding 12 patterns...")
            pat_embeds = embed_texts(pattern_texts, model_name, is_query=False)
            pat_vecs = {}
            for item in pat_embeds:
                pat_vecs[item["id"]] = normalize(item["embedding"])
            print(f"     ✅ Patterns embedded: {len(pat_vecs)}")

            # Step 2: Embed queries
            queries = [{"id": i, "text": t["query"]} for i, t in enumerate(tests)]
            print(f"  ⏳ Embedding {len(queries)} queries...")
            qry_embeds = embed_texts(queries, model_name, is_query=True)
            qry_vecs = {}
            for item in qry_embeds:
                qry_vecs[item["id"]] = normalize(item["embedding"])
            print(f"     ✅ Queries embedded: {len(qry_vecs)}")

        except Exception as e:
            print(f"     ❌ FAILED: {e}")
            all_results[model_label] = {"error": str(e)}
            continue

        # Step 3: Evaluate
        top1_correct = 0
        top5_correct = 0
        total_queries = len(tests)
        query_details = []

        for qi, test in enumerate(tests):
            qvec = qry_vecs[qi]
            ground_truth_types = set(test["ground_truth_patterns"])
            ground_truth_ids = set()
            for gt_type in ground_truth_types:
                if gt_type in type_to_id:
                    ground_truth_ids.add(type_to_id[gt_type])

            # Score all patterns
            scored = []
            for pid in pattern_ids:
                score = cosine_sim(qvec, pat_vecs[pid])
                scored.append((score, pid, pattern_map[pid]["pattern_type"]))

            scored.sort(reverse=True)

            top1_type = scored[0][2]
            top5_types = set(t[2] for t in scored[:5])

            # Check Top-1
            if top1_type in ground_truth_types:
                top1_correct += 1
                top1_ok = True
            else:
                top1_ok = False

            # Check Top-5
            if ground_truth_types & top5_types:
                top5_correct += 1
                top5_ok = True
            else:
                top5_ok = False

            query_details.append({
                "query": test["query"][:50],
                "ground_truth": ground_truth_types,
                "top1": top1_type,
                "top1_ok": top1_ok,
                "top5": top5_types,
                "top5_ok": top5_ok,
                "top3": [t[2] for t in scored[:3]],
                "top_scores": [round(t[0], 4) for t in scored[:5]],
            })

        top1_acc = top1_correct / total_queries * 100
        top5_acc = top5_correct / total_queries * 100

        all_results[model_label] = {
            "model": model_name,
            "top1_correct": top1_correct,
            "top1_total": total_queries,
            "top1_accuracy": top1_acc,
            "top5_correct": top5_correct,
            "top5_total": total_queries,
            "top5_accuracy": top5_acc,
            "details": query_details,
        }

        # Print summary for this model
        print(f"\n  📊 RESULTS:")
        print(f"     Top-1 Accuracy: {top1_correct}/{total_queries} = {top1_acc:.1f}%")
        print(f"     Top-5 Accuracy: {top5_correct}/{total_queries} = {top5_acc:.1f}%")

        # Show per-query breakdown
        print(f"\n  📋 Per-query breakdown:")
        for d in query_details:
            mark1 = "✅" if d["top1_ok"] else "❌"
            mark5 = "✅" if d["top5_ok"] else "❌"
            print(f"     T1:{mark1} T5:{mark5} | query: \"{d['query']}...\"")
            print(f"           Top-1: {d['top1']} | Top-3: {', '.join(d['top3'])}")
            print(f"           Scores: {d['top_scores']}")

    # ── Final Comparison ────────────────────────────────────────────
    print(f"\n{'=' * 72}")
    print("  📊 FINAL COMPARISON")
    print(f"{'=' * 72}\n")

    baseline = None
    for label, results in all_results.items():
        if "BASELINE" in label:
            baseline = results

    print(f"  {'Model':<40} {'Top-1':>10} {'Top-5':>10}")
    print(f"  {'─' * 62}")
    for label, results in all_results.items():
        if "error" in results:
            print(f"  {label:<40} {'ERROR':>10} {'':>10}")
            continue
        t1 = f"{results['top1_accuracy']:.1f}%"
        t5 = f"{results['top5_accuracy']:.1f}%"
        marker = ""
        if baseline and label != "multilingual-e5-small (BASELINE)":
            delta_t1 = results["top1_accuracy"] - baseline["top1_accuracy"]
            delta_t5 = results["top5_accuracy"] - baseline["top5_accuracy"]
            if delta_t1 > 0:
                marker = f" ▲+{delta_t1:.1f}%"
            elif delta_t1 < 0:
                marker = f" ▼{delta_t1:.1f}%"
            else:
                marker = "  ="
        print(f"  {label:<40} {t1:>10} {t5:>10}{marker}")

    # ── Detailed breakdown ──────────────────────────────────────────
    print(f"\n{'─' * 72}")
    print("  🔍 DETAILED PER-QUERY COMPARISON ACROSS MODELS")
    print(f"{'─' * 72}\n")

    # Table header
    models_list = list(all_results.keys())
    print(f"  {'Query':<45} ", end="")
    for label in models_list:
        short = label.split("(")[0].strip()[:20]
        print(f" {short:>12}", end="")
    print()

    for qi, test in enumerate(tests):
        q_short = test["query"][:43]
        print(f"  {q_short:<45}", end="")
        for label in models_list:
            if "error" in all_results[label]:
                print(f" {'ERR':>12}", end="")
            else:
                d = all_results[label]["details"][qi]
                t1 = d["top1"]
                gt = d["ground_truth"]
                if t1 in gt:
                    print(f" {'✅ ' + t1[:9]:>12}", end="")
                else:
                    print(f" {'❌ ' + t1[:9]:>12}", end="")
        print()

    # ── Recommendation ──────────────────────────────────────────────
    print(f"\n{'=' * 72}")
    print("  ✅ RECOMMENDATION")
    print(f"{'=' * 72}\n")

    # Find best model
    best_top1 = 0
    best_label = ""
    for label, results in all_results.items():
        if "error" not in results and results["top1_accuracy"] > best_top1:
            best_top1 = results["top1_accuracy"]
            best_label = label

    print(f"  Best Top-1 model: {best_label} ({best_top1:.1f}%)")

    # Trade-off analysis
    if baseline and all_results.get(best_label, {}).get("top1_accuracy", 0) > baseline["top1_accuracy"]:
        print(f"\n  ⚠️  TRADE-OFF: Better accuracy but LOSS of Hebrew query support")
        print(f"     - Hebrew transcripts (97% of content) → multilingual-e5 handles both")
        print(f"     - bge-small-en-v1.5 & all-MiniLM-L6-v2 are ENGLISH ONLY")
        print(f"     - If users query in Hebrew, English-only models will FAIL silently")
        print(f"     - If queries are always in English, switch to better model")
        print(f"\n  📌 RECOMMENDATION:")
        if "bge" in best_label.lower():
            print(f"     → KEEP multilingual-e5-small as primary model")
            print(f"     → Use bge-small-en-v1.5 as secondary for English queries")
        else:
            print(f"     → Stay with multilingual-e5-small unless you can ensure all")
            print(f"       user queries will be in English")
    elif baseline:
        print(f"\n  ✅ BASELINE wins or ties: multilingual-e5-small is the best choice")
        print(f"     No benefit from switching, and would lose Hebrew support.")

    # Print best vs baseline detail
    if baseline:
        print(f"\n  📊 Accuracy Comparison:")
        best = all_results.get(best_label, baseline)
        base_label = "multilingual-e5-small (BASELINE)"
        print(f"     {base_label:<35} Top-1: {baseline['top1_accuracy']:.1f}%  Top-5: {baseline['top5_accuracy']:.1f}%")
        if best_label != base_label:
            print(f"     {best_label:<35} Top-1: {best['top1_accuracy']:.1f}%  Top-5: {best['top5_accuracy']:.1f}%")
            delta_t1 = best['top1_accuracy'] - baseline['top1_accuracy']
            delta_t5 = best['top5_accuracy'] - baseline['top5_accuracy']
            print(f"     {'Difference':>35}     Δ = {'+' if delta_t1>0 else ''}{delta_t1:.1f}%        Δ = {'+' if delta_t5>0 else ''}{delta_t5:.1f}%")

    print(f"\n{'=' * 72}")


if __name__ == "__main__":
    run_test()
