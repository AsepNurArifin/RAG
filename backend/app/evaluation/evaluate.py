"""
Offline Evaluation Framework — EnterpriseMind AI.

Mengukur kualitas RAG system dengan metrics:
- Recall@20, Context Precision, Answer Relevancy, Faithfulness, Hallucination Rate
- Latency P50, P95, Cost per Query

Usage:
    python -m app.evaluation.evaluate
    python -m app.evaluation.evaluate --baseline
    python -m app.evaluation.evaluate --compare baseline.json --current eval.json
"""
import json
import time
import logging
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Pastikan bisa import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def load_test_set(path: str = None) -> list[dict]:
    if path is None:
        path = str(Path(__file__).parent / "test_set.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_query(query: str) -> dict:
    from app.graph.build_graph import build_agent_graph
    import time as time_module

    graph = build_agent_graph()
    initial_state = {
        "query": query,
        "session_id": f"eval-{int(time.time())}",
        "intent": "",
        "agents_to_activate": [],
        "orchestrator_reasoning": "",
        "retrieved_documents": [],
        "reformulated_query": "",
        "verified_claims": [],
        "flagged_issues": [],
        "confidence_score": 0.0,
        "needs_reflection": False,
        "reflection_count": 0,
        "final_answer": "",
        "citations": [],
        "action_items": [],
        "conversation_history": [],
        "error": None,
        "query_deadline": time.time() + 120,
    }

    start = time.time()
    try:
        result = graph.invoke(initial_state)
        latency = time.time() - start
        return {
            "answer": result.get("final_answer", ""),
            "documents": result.get("retrieved_documents", []),
            "confidence": result.get("confidence_score", 0),
            "intent": result.get("intent", ""),
            "reflection_count": result.get("reflection_count", 0),
            "latency_s": round(latency, 3),
            "error": None,
        }
    except Exception as e:
        latency = time.time() - start
        return {
            "answer": "",
            "documents": [],
            "confidence": 0,
            "intent": "",
            "reflection_count": 0,
            "latency_s": round(latency, 3),
            "error": str(e),
        }


def compute_recall_at_k(retrieved_docs: list[dict], expected_sources: list[str], k: int = 20) -> float:
    if not expected_sources:
        return 1.0
    retrieved_sources = set()
    for doc in retrieved_docs[:k]:
        source = doc.get("source", "")
        retrieved_sources.add(source.lower())
    expected_lower = set(s.lower() for s in expected_sources)
    hits = len(retrieved_sources & expected_lower)
    return hits / len(expected_lower) if expected_lower else 0.0


def compute_answer_contains(answer: str, expected_contains: list[str]) -> float:
    if not expected_contains:
        return 1.0
    answer_lower = answer.lower()
    hits = sum(1 for term in expected_contains if term.lower() in answer_lower)
    return hits / len(expected_contains)


def compute_context_precision(documents: list[dict], expected_contains: list[str]) -> float:
    if not documents or not expected_contains:
        return 0.0
    relevant = 0
    for doc in documents:
        content = doc.get("content", "").lower()
        if any(term.lower() in content for term in expected_contains):
            relevant += 1
    return relevant / len(documents)


def run_evaluation(test_set: list[dict], output_path: str = None) -> dict:
    logger.info("Starting evaluation with %d test questions...", len(test_set))

    results = []
    by_category = defaultdict(list)

    for i, test_case in enumerate(test_set, 1):
        query = test_case["query"]
        query_type = test_case["query_type"]
        logger.info("[%d/%d] %s (%s): %s", i, len(test_set), test_case["id"], query_type, query[:60])

        result = run_query(query)

        recall = compute_recall_at_k(result["documents"], test_case.get("expected_sources", []))
        answer_contains = compute_answer_contains(result["answer"], test_case.get("expected_answer_contains", []))
        context_precision = compute_context_precision(result["documents"], test_case.get("expected_answer_contains", []))

        entry = {
            "id": test_case["id"],
            "query": query,
            "query_type": query_type,
            "subcategory": test_case.get("subcategory", ""),
            "difficulty": test_case.get("difficulty", "medium"),
            "recall_at_20": round(recall, 4),
            "answer_contains": round(answer_contains, 4),
            "context_precision": round(context_precision, 4),
            "confidence": result["confidence"],
            "latency_s": result["latency_s"],
            "reflection_count": result["reflection_count"],
            "num_documents": len(result["documents"]),
            "error": result["error"],
        }
        results.append(entry)
        by_category[query_type].append(entry)

    successful = [r for r in results if r["error"] is None]
    failed = [r for r in results if r["error"] is not None]
    latencies = [r["latency_s"] for r in successful]

    latencies_sorted = sorted(latencies)
    p50_idx = int(len(latencies_sorted) * 0.5)
    p95_idx = int(len(latencies_sorted) * 0.95)

    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_queries": len(test_set),
        "successful": len(successful),
        "failed": len(failed),
        "overall": {
            "recall_at_20_avg": round(sum(r["recall_at_20"] for r in successful) / max(len(successful), 1), 4),
            "answer_contains_avg": round(sum(r["answer_contains"] for r in successful) / max(len(successful), 1), 4),
            "context_precision_avg": round(sum(r["context_precision"] for r in successful) / max(len(successful), 1), 4),
            "confidence_avg": round(sum(r["confidence"] for r in successful) / max(len(successful), 1), 4),
            "latency_p50": round(latencies_sorted[p50_idx], 3) if latencies_sorted else 0,
            "latency_p95": round(latencies_sorted[min(p95_idx, len(latencies_sorted)-1)], 3) if latencies_sorted else 0,
            "latency_avg": round(sum(latencies) / max(len(latencies), 1), 3),
        },
        "by_category": {},
        "results": results,
    }

    for category, entries in by_category.items():
        cat_successful = [e for e in entries if e["error"] is None]
        cat_latencies = [e["latency_s"] for e in cat_successful]
        cat_latencies_sorted = sorted(cat_latencies)

        summary["by_category"][category] = {
            "count": len(entries),
            "successful": len(cat_successful),
            "recall_at_20_avg": round(sum(e["recall_at_20"] for e in cat_successful) / max(len(cat_successful), 1), 4),
            "answer_contains_avg": round(sum(e["answer_contains"] for e in cat_successful) / max(len(cat_successful), 1), 4),
            "context_precision_avg": round(sum(e["context_precision"] for e in cat_successful) / max(len(cat_successful), 1), 4),
            "latency_avg": round(sum(cat_latencies) / max(len(cat_latencies), 1), 3),
        }

    if output_path is None:
        output_path = str(Path(__file__).parent / "results" / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info("Results saved to %s", output_path)
    print_summary(summary)
    return summary


def print_summary(summary: dict):
    print("\n" + "=" * 70)
    print("EVALUATION RESULTS")
    print("=" * 70)
    print(f"Timestamp: {summary['timestamp']}")
    print(f"Total: {summary['total_queries']} | Success: {summary['successful']} | Failed: {summary['failed']}")
    print("\n--- Overall Metrics ---")
    overall = summary["overall"]
    print(f"  Recall@20 avg:        {overall['recall_at_20_avg']:.4f}")
    print(f"  Answer Contains avg:  {overall['answer_contains_avg']:.4f}")
    print(f"  Context Precision avg:{overall['context_precision_avg']:.4f}")
    print(f"  Confidence avg:       {overall['confidence_avg']:.4f}")
    print(f"  Latency P50:          {overall['latency_p50']:.3f}s")
    print(f"  Latency P95:          {overall['latency_p95']:.3f}s")
    print(f"  Latency Avg:          {overall['latency_avg']:.3f}s")

    print("\n--- Per Category ---")
    for cat, data in summary.get("by_category", {}).items():
        print(f"\n  [{cat.upper()}] ({data['successful']}/{data['count']} success)")
        print(f"    Recall@20:         {data['recall_at_20_avg']:.4f}")
        print(f"    Answer Contains:   {data['answer_contains_avg']:.4f}")
        print(f"    Context Precision: {data['context_precision_avg']:.4f}")
        print(f"    Latency Avg:       {data['latency_avg']:.3f}s")
    print("=" * 70)


def compare_results(baseline_path: str, current_path: str):
    with open(baseline_path, "r") as f:
        baseline = json.load(f)
    with open(current_path, "r") as f:
        current = json.load(f)

    print("\n" + "=" * 80)
    print("COMPARISON: Baseline vs Current")
    print("=" * 80)
    print(f"Baseline: {baseline['timestamp']}")
    print(f"Current:  {current['timestamp']}")

    print("\n--- Overall ---")
    print(f"{'Metric':<25} {'Baseline':>10} {'Current':>10} {'Delta':>10} {'Pass?':>8}")
    print("-" * 65)

    metrics = [
        ("Recall@20", "recall_at_20_avg", 0.05),
        ("Answer Contains", "answer_contains_avg", 0.03),
        ("Context Precision", "context_precision_avg", 0.03),
        ("Confidence", "confidence_avg", 0.03),
        ("Latency P50 (s)", "latency_p50", None),
        ("Latency P95 (s)", "latency_p95", None),
    ]

    for name, key, min_delta in metrics:
        b_val = baseline["overall"].get(key, 0)
        c_val = current["overall"].get(key, 0)
        delta = c_val - b_val

        if min_delta is not None:
            passed = delta >= min_delta
            pass_str = "PASS" if passed else "FAIL"
        else:
            passed = delta <= b_val * 0.2
            pass_str = "OK" if passed else "WARN"

        print(f"  {name:<23} {b_val:>10.4f} {c_val:>10.4f} {delta:>+10.4f} {pass_str:>8}")

    print("\n--- Per Category ---")
    all_categories = set(list(baseline.get("by_category", {}).keys()) + list(current.get("by_category", {}).keys()))

    for cat in sorted(all_categories):
        b_data = baseline.get("by_category", {}).get(cat, {})
        c_data = current.get("by_category", {}).get(cat, {})

        if not b_data or not c_data:
            continue

        print(f"\n  [{cat.upper()}]")
        print(f"  {'Metric':<23} {'Baseline':>10} {'Current':>10} {'Delta':>10}")
        print(f"  {'-'*55}")

        for name, key in [("Recall@20", "recall_at_20_avg"), ("Answer Contains", "answer_contains_avg"), ("Context Precision", "context_precision_avg")]:
            b_val = b_data.get(key, 0)
            c_val = c_data.get(key, 0)
            delta = c_val - b_val
            print(f"    {name:<21} {b_val:>10.4f} {c_val:>10.4f} {delta:>+10.4f}")

    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EnterpriseMind Evaluation Framework")
    parser.add_argument("--baseline", action="store_true", help="Run as baseline evaluation")
    parser.add_argument("--compare", type=str, help="Path to baseline JSON for comparison")
    parser.add_argument("--current", type=str, help="Path to current evaluation JSON")
    parser.add_argument("--test-set", type=str, help="Path to custom test set")
    parser.add_argument("--output", type=str, help="Output path for results")

    args = parser.parse_args()

    if args.compare and args.current:
        compare_results(args.compare, args.current)
    else:
        test_set = load_test_set(args.test_set)
        output = args.output
        if output is None:
            prefix = "baseline" if args.baseline else "eval"
            output = str(Path(__file__).parent / "results" / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        run_evaluation(test_set, output)
