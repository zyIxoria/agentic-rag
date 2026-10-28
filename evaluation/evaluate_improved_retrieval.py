"""evaluate_improved_retrieval.py - Script đánh giá định lượng đối chứng đa phiên bản (V0 — V4).

Thực hiện đo lường khoa học trên toàn bộ 80 câu hỏi của benchmark RAG-08 (evaluation/dataset/legal_qa.json):
- Giữ nguyên 100% nội dung câu hỏi, gold labels và công thức tính metrics chuẩn mực.
- Chạy đối chứng tuần tự:
  + V0: Baseline Dense Retriever (all-MiniLM-L6-v2, top-k=5).
  + V1: Query Expansion + Dense.
  + V2: Hybrid Retrieval (Dense + BM25 + RRF).
  + V3: Hybrid + Deep Interaction Cross Reranker.
  + V4: Full Pipeline (+ Relevance Gate).
- Xuất kết quả chi tiết ra evaluation/results/improved_retrieval_comparison.json.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
import statistics
import sys
import time
from typing import Any, Dict, List, Set, Tuple

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from RAG.pipeline.improved_rag import ImprovedRAGPipeline
from RAG.retriever.schema import RetrievedChunk

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_improved_retrieval")


def evaluate_version(version: str, benchmark: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Đánh giá toàn diện một phiên bản trên 80 câu hỏi benchmark."""
    logger.info(f"=== Bắt đầu đánh giá phiên bản: {version} ===")
    from RAG.pipeline.config import PipelineConfig
    cfg = PipelineConfig(LLM_PROVIDER="mock")
    pipeline = ImprovedRAGPipeline(version=version, config=cfg)

    k_list = [1, 3, 5, 10]
    latencies: List[float] = []

    # Danh sách gom số liệu của 64 câu hỏi answerable
    metrics_sum: Dict[str, float] = {
        "hit_rate@1": 0.0,
        "recall_chunk@1": 0.0,
        "precision_chunk@1": 0.0,
        "article_hit_rate@1": 0.0,
        "recall_article@1": 0.0,
        "hit_rate@3": 0.0,
        "recall_chunk@3": 0.0,
        "precision_chunk@3": 0.0,
        "article_hit_rate@3": 0.0,
        "recall_article@3": 0.0,
        "hit_rate@5": 0.0,
        "recall_chunk@5": 0.0,
        "precision_chunk@5": 0.0,
        "article_hit_rate@5": 0.0,
        "recall_article@5": 0.0,
        "hit_rate@10": 0.0,
        "recall_chunk@10": 0.0,
        "precision_chunk@10": 0.0,
        "article_hit_rate@10": 0.0,
        "recall_article@10": 0.0,
        "mrr_chunk": 0.0,
        "mrr_article": 0.0,
    }

    answerable_count = 0
    refusal_count = 0
    correct_refusals = 0

    per_question_results: List[Dict[str, Any]] = []

    for item in benchmark:
        qid = item["question_id"]
        q_text = item["question"].strip()
        cat = item["category"]
        requires_refusal = item["requires_refusal"]
        gold_sources = item.get("gold_sources", [])

        gold_chunk_ids: Set[str] = set()
        gold_articles: Set[Tuple[str, str]] = set()
        for gs in gold_sources:
            doc_id = gs["document_id"]
            art_num = gs.get("article_number") or ""
            gold_articles.add((doc_id, art_num))
            for cid in gs.get("chunk_ids", []):
                gold_chunk_ids.add(cid)

        # Thực thi pipeline
        t0 = time.perf_counter()
        resp = pipeline.answer(q_text, top_k=10)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed_ms)

        retrieved_chunks = resp.retrieved_chunks

        # Đánh giá cho câu hỏi refusal
        if requires_refusal:
            refusal_count += 1
            if resp.refused:
                correct_refusals += 1
            per_question_results.append({
                "question_id": qid,
                "category": cat,
                "requires_refusal": True,
                "system_refused": resp.refused,
                "latency_ms": round(elapsed_ms, 2)
            })
            continue

        # Đánh giá cho câu hỏi answerable
        answerable_count += 1

        # Tính MRR
        mrr_chunk = 0.0
        for rank, c in enumerate(retrieved_chunks, start=1):
            if c.chunk_id in gold_chunk_ids:
                mrr_chunk = 1.0 / rank
                break

        mrr_article = 0.0
        for rank, c in enumerate(retrieved_chunks, start=1):
            c_doc = c.metadata.get("document_id", "")
            c_art = c.metadata.get("article_number") or ""
            if (c_doc, c_art) in gold_articles:
                mrr_article = 1.0 / rank
                break

        metrics_sum["mrr_chunk"] += mrr_chunk
        metrics_sum["mrr_article"] += mrr_article

        q_metrics: Dict[str, Any] = {
            "question_id": qid,
            "category": cat,
            "requires_refusal": False,
            "mrr_chunk": round(mrr_chunk, 4),
            "mrr_article": round(mrr_article, 4),
            "latency_ms": round(elapsed_ms, 2)
        }

        for k in k_list:
            top_k_chunks = retrieved_chunks[:k]
            top_k_ids = {c.chunk_id for c in top_k_chunks}
            top_k_articles = {
                (c.metadata.get("document_id", ""), c.metadata.get("article_number") or "")
                for c in top_k_chunks
            }

            chunks_matched = top_k_ids & gold_chunk_ids
            hit_k = 1 if chunks_matched else 0
            recall_chunk = len(chunks_matched) / len(gold_chunk_ids) if gold_chunk_ids else 0.0
            precision_chunk = len(chunks_matched) / k

            articles_matched = top_k_articles & gold_articles
            art_hit_k = 1 if articles_matched else 0
            recall_art = len(articles_matched) / len(gold_articles) if gold_articles else 0.0
            precision_art = len(articles_matched) / k

            metrics_sum[f"hit_rate@{k}"] += hit_k
            metrics_sum[f"recall_chunk@{k}"] += recall_chunk
            metrics_sum[f"precision_chunk@{k}"] += precision_chunk
            metrics_sum[f"article_hit_rate@{k}"] += art_hit_k
            metrics_sum[f"recall_article@{k}"] += recall_art

            q_metrics[f"recall_chunk@{k}"] = round(recall_chunk, 4)
            q_metrics[f"hit_rate@{k}"] = hit_k
            q_metrics[f"article_hit_rate@{k}"] = art_hit_k

        per_question_results.append(q_metrics)

    # Tính trung bình cộng trên các câu answerable
    averaged_metrics: Dict[str, float] = {}
    for metric_name, total_val in metrics_sum.items():
        averaged_metrics[metric_name] = round(total_val / max(1, answerable_count), 4)

    refusal_precision = round(correct_refusals / max(1, refusal_count), 4) if refusal_count else 0.0

    latency_summary = {
        "mean_ms": round(statistics.mean(latencies), 2),
        "median_ms": round(statistics.median(latencies), 2),
        "p95_ms": round(sorted(latencies)[int(0.95 * len(latencies))], 2),
    }

    logger.info(
        f"Hoàn tất {version}: Hit@5={averaged_metrics['hit_rate@5']*100:.1f}%, "
        f"RecallChunk@5={averaged_metrics['recall_chunk@5']*100:.1f}%, "
        f"ArticleHit@5={averaged_metrics['article_hit_rate@5']*100:.1f}%, "
        f"MRR_Article={averaged_metrics['mrr_article']:.4f}, "
        f"RefusalPrecision={refusal_precision*100:.1f}%, "
        f"MeanLatency={latency_summary['mean_ms']}ms"
    )

    return {
        "version": version,
        "answerable_count": answerable_count,
        "refusal_count": refusal_count,
        "refusal_precision": refusal_precision,
        "overall_metrics": averaged_metrics,
        "latency": latency_summary,
        "per_question_sample": per_question_results[:5]
    }


def main():
    benchmark_path = project_root / "evaluation" / "dataset" / "legal_qa.json"
    with open(benchmark_path, "r", encoding="utf-8") as f:
        benchmark: List[Dict[str, Any]] = json.load(f)

    logger.info(f"Loaded benchmark with {len(benchmark)} questions.")

    versions_to_evaluate = ["V0", "V1", "V2", "V3", "V4"]
    all_results = {}

    for v in versions_to_evaluate:
        res = evaluate_version(v, benchmark)
        all_results[v] = res

    out_path = project_root / "evaluation" / "results" / "improved_retrieval_comparison.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    logger.info(f"Đã lưu toàn bộ kết quả benchmark vào: {out_path}")


if __name__ == "__main__":
    main()
