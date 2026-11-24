"""Retrieval evaluation against evals/golden.jsonl (document-level relevance, so every chunking strategy is
scored on the same labels).

recall@k: share of a question's gold documents that appear among the top-k chunks, averaged over questions.
MRR:      1 / rank of the first chunk from a gold document (top 10), averaged.
Only `answerable` and `multi-doc` items are scored; `unanswerable` items feed the abstention analysis
(how well the top vector similarity separates answerable from unanswerable questions).
"""
import json
import statistics
import time
from pathlib import Path

from . import retrieval

GOLDEN = Path(__file__).resolve().parent.parent / "evals" / "golden.jsonl"
KS = (1, 3, 5)


def load_golden(path: Path = GOLDEN) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def score_ranking(docs: list[str], gold: list[str]) -> dict:
    out = {f"recall@{k}": len(set(docs[:k]) & set(gold)) / len(gold) for k in KS}
    rank = next((i for i, d in enumerate(docs[:10], start=1) if d in gold), None)
    out["mrr"] = 1 / rank if rank else 0.0
    return out


def eval_config(conn, index_name: str, mode: str, items: list[dict]) -> dict:
    rows, latencies = [], []
    for it in items:
        t0 = time.perf_counter()
        hits = retrieval.search(conn, index_name, it["question"], k=10, mode=mode)
        latencies.append((time.perf_counter() - t0) * 1000)
        r = score_ranking([h.doc_id for h in hits], it["gold_docs"])
        r.update(id=it["id"], type=it["type"], split=it["split"])
        rows.append(r)
    def agg(sel):
        return {m: round(statistics.mean(r[m] for r in sel), 3) for m in [f"recall@{k}" for k in KS] + ["mrr"]} | {"n": len(sel)}
    return {
        "index": index_name, "mode": mode,
        "dev": agg([r for r in rows if r["split"] == "dev"]),
        "holdout": agg([r for r in rows if r["split"] == "holdout"]),
        "multi_doc": agg([r for r in rows if r["type"] == "multi-doc"]),
        "p50_ms": round(statistics.median(latencies), 1),
        "per_question": rows,
    }


def abstention(conn, index_name: str, golden: list[dict]) -> dict:
    """Top-1 cosine similarity for answerable vs unanswerable questions, and the best single threshold."""
    sims = []
    for it in golden:
        if it["type"] == "injection":
            continue
        top = retrieval.vector(conn, index_name, it["question"], 1)[0].score
        sims.append((top, it["type"] != "unanswerable"))
    best = max(((t, sum((s >= t) == ans for s, ans in sims) / len(sims)) for t, _ in sims), key=lambda x: x[1])
    ans = [s for s, a in sims if a]
    una = [s for s, a in sims if not a]
    return {"index": index_name, "answerable_min": round(min(ans), 3), "answerable_p10": round(sorted(ans)[len(ans) // 10], 3),
            "unanswerable_max": round(max(una), 3), "best_threshold": round(best[0], 3), "best_accuracy": round(best[1], 3)}
