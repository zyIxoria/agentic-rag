"""evaluate_retrieval.py - Script thực thi đánh giá Dense Retrieval Baseline (TASK RAG-09).

Đánh giá toàn diện trên 80 câu hỏi của benchmark RAG-08 (evaluation/dataset/legal_qa.json):
- Đo đạc thời gian: embedding latency, vector search latency, total retrieval latency (mean, median, p95).
- Tính toán metrics: Recall@K, Precision@K, Hit Rate@K, MRR (với K in [1, 3, 5, 10]).
- Phân định rõ cả Chunk-level và Article-level metrics cho các câu hỏi đa văn bản / đa chunk.
- Phân rã theo từng danh mục (Category Breakdown: A-G).
- Phát hiện và phân loại chi tiết các failure modes (Error Analysis) lưu trữ tối thiểu 20+ trường hợp.
- Xuất dữ liệu đánh giá đầy đủ ra evaluation/results/retrieval_baseline.json.
"""

from __future__ import annotations
import json
import logging
import os
from pathlib import Path
import statistics
import sys
import time
from typing import Any, Dict, List, Set, Tuple

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from RAG.embedding.embeddings import get_embedding_provider
from RAG.retriever.config import default_retriever_config
from RAG.retriever.dense_retriever import DenseTopKRetriever
from RAG.retriever.schema import RetrievedChunk
from RAG.vector_store.chroma_store import PersistentChromaStore
from RAG.vector_store.schema import desanitize_metadata

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_retrieval")


def calculate_percentiles(values: List[float]) -> Dict[str, float]:
    """Tính mean, median, p95 cho danh sách số liệu thực."""
    if not values:
        return {"mean": 0.0, "median": 0.0, "p95": 0.0, "min": 0.0, "max": 0.0}
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    p95_idx = min(int(0.95 * n), n - 1)
    return {
        "mean": round(statistics.mean(values), 2),
        "median": round(statistics.median(values), 2),
        "p95": round(sorted_vals[p95_idx], 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
    }


def run_evaluation() -> Dict[str, Any]:
    project_root = Path(__file__).resolve().parent.parent
    benchmark_path = project_root / "evaluation" / "dataset" / "legal_qa.json"
    results_dir = project_root / "evaluation" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    results_output_path = results_dir / "retrieval_baseline.json"

    logger.info(f"Loading benchmark from: {benchmark_path}")
    with open(benchmark_path, "r", encoding="utf-8") as f:
        benchmark: List[Dict[str, Any]] = json.load(f)

    logger.info(f"Benchmark contains {len(benchmark)} questions.")

    # Khởi tạo Vector Store và Retriever độc lập
    chroma_store = PersistentChromaStore(persist_directory=default_retriever_config.PERSIST_DIRECTORY)
    embedding_provider = get_embedding_provider()
    chroma_store.load_collection(
        name=default_retriever_config.COLLECTION_NAME,
        expected_dimension=embedding_provider.dimension,
        expected_model=embedding_provider.model_name,
    )
    retriever = DenseTopKRetriever(
        vector_store=chroma_store,
        embedding_provider=embedding_provider,
    )

    logger.info(f"Loaded vector store with {chroma_store.count()} chunks. Beginning evaluation...")

    per_question_results: List[Dict[str, Any]] = []
    embedding_latencies: List[float] = []
    vector_search_latencies: List[float] = []
    total_latencies: List[float] = []

    # Danh sách thu thập lỗi phục vụ Error Analysis
    failure_cases: List[Dict[str, Any]] = []

    k_list = [1, 3, 5, 10]

    for item_idx, item in enumerate(benchmark, start=1):
        qid = item["question_id"]
        q_text = item["question"].strip()
        cat = item["category"]
        requires_refusal = item["requires_refusal"]
        gold_sources = item.get("gold_sources", [])

        # Tập hợp gold chunk IDs và gold articles
        gold_chunk_ids: Set[str] = set()
        gold_articles: Set[Tuple[str, str]] = set()
        for gs in gold_sources:
            doc_id = gs["document_id"]
            art_num = gs.get("article_number") or ""
            gold_articles.add((doc_id, art_num))
            for cid in gs.get("chunk_ids", []):
                gold_chunk_ids.add(cid)

        # 1. Đo lường Embedding Latency
        t0 = time.perf_counter()
        query_vector = retriever.embedding_provider.embed_text(q_text)
        t1 = time.perf_counter()
        emb_latency_ms = (t1 - t0) * 1000.0

        # 2. Đo lường Vector Search Latency (Top-10)
        chroma_res = retriever.vector_store.collection.query(
            query_embeddings=[query_vector],
            n_results=10,
            include=["documents", "metadatas", "distances"],
        )
        t2 = time.perf_counter()
        search_latency_ms = (t2 - t1) * 1000.0
        total_latency_ms = (t2 - t0) * 1000.0

        embedding_latencies.append(emb_latency_ms)
        vector_search_latencies.append(search_latency_ms)
        total_latencies.append(total_latency_ms)

        raw_ids = chroma_res.get("ids", [[]])[0]
        raw_docs = chroma_res.get("documents", [[]])[0]
        raw_metas = chroma_res.get("metadatas", [[]])[0]
        raw_dists = chroma_res.get("distances", [[]])[0]

        retrieved_chunks: List[RetrievedChunk] = []
        for i in range(len(raw_ids)):
            cid = raw_ids[i]
            doc = raw_docs[i] if i < len(raw_docs) else ""
            dist = float(raw_dists[i]) if i < len(raw_dists) else 1.0
            sim = 1.0 - dist
            meta = desanitize_metadata(raw_metas[i] if i < len(raw_metas) else {}, restore_none=True)
            retrieved_chunks.append(
                RetrievedChunk(
                    chunk_id=cid,
                    content=doc,
                    score=round(sim, 6),
                    distance=round(dist, 6),
                    metadata=meta,
                    rank=i + 1,
                )
            )

        # Sắp xếp lại theo score giảm dần để chắc chắn
        retrieved_chunks.sort(key=lambda c: c.score, reverse=True)
        for rank_idx, chunk in enumerate(retrieved_chunks, start=1):
            chunk.rank = rank_idx

        # 3. Tính toán metrics
        metrics: Dict[str, Any] = {}
        error_flags: List[str] = []

        if not requires_refusal:
            # Metrics cho câu hỏi cần trả lời
            for k in k_list:
                top_k_chunks = retrieved_chunks[:k]
                top_k_ids = {c.chunk_id for c in top_k_chunks}
                top_k_articles = {
                    (c.metadata.get("document_id", ""), c.metadata.get("article_number", "") or "")
                    for c in top_k_chunks
                }

                # Chunk-level
                chunks_matched = top_k_ids & gold_chunk_ids
                hit_k = 1 if len(chunks_matched) > 0 else 0
                recall_chunk = len(chunks_matched) / len(gold_chunk_ids) if gold_chunk_ids else 0.0
                precision_chunk = len(chunks_matched) / k

                # Article-level
                articles_matched = top_k_articles & gold_articles
                article_hit_k = 1 if len(articles_matched) > 0 else 0
                recall_art = len(articles_matched) / len(gold_articles) if gold_articles else 0.0
                precision_art = len(articles_matched) / k

                metrics[f"hit_rate@{k}"] = hit_k
                metrics[f"recall_chunk@{k}"] = round(recall_chunk, 4)
                metrics[f"precision_chunk@{k}"] = round(precision_chunk, 4)
                metrics[f"article_hit_rate@{k}"] = article_hit_k
                metrics[f"recall_article@{k}"] = round(recall_art, 4)
                metrics[f"precision_article@{k}"] = round(precision_art, 4)

            # MRR (Chunk & Article)
            mrr_chunk = 0.0
            for c in retrieved_chunks:
                if c.chunk_id in gold_chunk_ids:
                    mrr_chunk = 1.0 / c.rank
                    break
            metrics["mrr_chunk"] = round(mrr_chunk, 4)

            mrr_article = 0.0
            for c in retrieved_chunks:
                art = (c.metadata.get("document_id", ""), c.metadata.get("article_number", "") or "")
                if art in gold_articles:
                    mrr_article = 1.0 / c.rank
                    break
            metrics["mrr_article"] = round(mrr_article, 4)

            # 4. Error Analysis Detection
            # a. Missed gold source completely in Top-10
            missed_chunks = gold_chunk_ids - {c.chunk_id for c in retrieved_chunks}
            if missed_chunks:
                error_flags.append("missed_gold_source")

            # b. Zero hit in Top-5
            if metrics["hit_rate@5"] == 0:
                error_flags.append("zero_hit_at_5")

            # c. Wrong document in rank 1
            top1_doc = retrieved_chunks[0].metadata.get("document_id", "") if retrieved_chunks else ""
            gold_doc_ids = {doc_id for (doc_id, _) in gold_articles}
            if top1_doc not in gold_doc_ids:
                error_flags.append("wrong_document_rank1")

            # d. Wrong article in rank 1
            top1_art = (
                retrieved_chunks[0].metadata.get("document_id", ""),
                retrieved_chunks[0].metadata.get("article_number", "") or "",
            ) if retrieved_chunks else ("", "")
            if top1_art not in gold_articles:
                error_flags.append("wrong_article_rank1")

            # e. Low-score correct result (correct chunk has score < 0.60)
            for c in retrieved_chunks:
                if c.chunk_id in gold_chunk_ids and c.score < 0.60:
                    error_flags.append(f"low_score_correct (score={c.score})")
                    break

            # f. High-score irrelevant result (irrelevant chunk in top-3 has score >= 0.70)
            for c in retrieved_chunks[:3]:
                if c.chunk_id not in gold_chunk_ids and (
                    (c.metadata.get("document_id", ""), c.metadata.get("article_number", "") or "") not in gold_articles
                ):
                    if c.score >= 0.70:
                        error_flags.append(f"high_score_irrelevant (rank={c.rank}, score={c.score})")
                        break

            # Thu thập failure cases
            if error_flags:
                failure_cases.append({
                    "question_id": qid,
                    "question": q_text,
                    "category": cat,
                    "error_types": error_flags,
                    "hit_at_5": metrics["hit_rate@5"],
                    "recall_chunk_at_5": metrics["recall_chunk@5"],
                    "gold_chunks": list(gold_chunk_ids),
                    "gold_articles": [f"{d}:{a}" for (d, a) in gold_articles],
                    "top_retrieved": [
                        {
                            "rank": c.rank,
                            "chunk_id": c.chunk_id,
                            "score": c.score,
                            "doc_id": c.metadata.get("document_id", ""),
                            "article": c.metadata.get("article_number", ""),
                            "is_gold_chunk": c.chunk_id in gold_chunk_ids,
                            "is_gold_article": (c.metadata.get("document_id", ""), c.metadata.get("article_number", "") or "") in gold_articles,
                            "content_preview": c.content[:150] + "..." if len(c.content) > 150 else c.content,
                        }
                        for c in retrieved_chunks[:5]
                    ]
                })

        else:
            # Metrics cho câu hỏi từ chối (insufficient_evidence & out_of_scope)
            # Đối với nhóm này, không có chunk vàng. Thu hồi chunk điểm cao là False Positive.
            max_score = retrieved_chunks[0].score if retrieved_chunks else 0.0
            avg_top5_score = (
                sum(c.score for c in retrieved_chunks[:5]) / min(len(retrieved_chunks), 5)
                if retrieved_chunks else 0.0
            )
            metrics["max_score"] = round(max_score, 4)
            metrics["avg_top5_score"] = round(avg_top5_score, 4)
            metrics["high_confidence_false_alarm"] = bool(max_score >= 0.65)

            if max_score >= 0.65:
                error_flags.append(f"false_positive_high_confidence (max_score={max_score})")

            failure_cases.append({
                "question_id": qid,
                "question": q_text,
                "category": cat,
                "error_types": error_flags or ["refusal_baseline_profile"],
                "hit_at_5": 0,
                "recall_chunk_at_5": 0.0,
                "gold_chunks": [],
                "gold_articles": [],
                "top_retrieved": [
                    {
                        "rank": c.rank,
                        "chunk_id": c.chunk_id,
                        "score": c.score,
                        "doc_id": c.metadata.get("document_id", ""),
                        "article": c.metadata.get("article_number", ""),
                        "is_gold_chunk": False,
                        "is_gold_article": False,
                        "content_preview": c.content[:150] + "..." if len(c.content) > 150 else c.content,
                    }
                    for c in retrieved_chunks[:5]
                ]
            })

        per_question_results.append({
            "question_id": qid,
            "question": q_text,
            "category": cat,
            "requires_refusal": requires_refusal,
            "embedding_latency_ms": round(emb_latency_ms, 2),
            "vector_search_latency_ms": round(search_latency_ms, 2),
            "total_latency_ms": round(total_latency_ms, 2),
            "metrics": metrics,
            "error_flags": error_flags,
            "retrieved_top10": [
                {
                    "rank": c.rank,
                    "chunk_id": c.chunk_id,
                    "score": c.score,
                    "document_id": c.metadata.get("document_id", ""),
                    "article_number": c.metadata.get("article_number", ""),
                }
                for c in retrieved_chunks
            ],
        })

    # ================== TÍNH TOÁN METRICS TỔNG THỂ & PHÂN RÃ CATEGORY ==================
    answerable_results = [r for r in per_question_results if not r["requires_refusal"]]
    refusal_results = [r for r in per_question_results if r["requires_refusal"]]

    def aggregate_metrics(results_subset: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not results_subset:
            return {}
        n = len(results_subset)
        agg: Dict[str, Any] = {}
        for k in k_list:
            agg[f"hit_rate@{k}"] = round(sum(r["metrics"][f"hit_rate@{k}"] for r in results_subset) / n, 4)
            agg[f"recall_chunk@{k}"] = round(sum(r["metrics"][f"recall_chunk@{k}"] for r in results_subset) / n, 4)
            agg[f"precision_chunk@{k}"] = round(sum(r["metrics"][f"precision_chunk@{k}"] for r in results_subset) / n, 4)
            agg[f"article_hit_rate@{k}"] = round(sum(r["metrics"][f"article_hit_rate@{k}"] for r in results_subset) / n, 4)
            agg[f"recall_article@{k}"] = round(sum(r["metrics"][f"recall_article@{k}"] for r in results_subset) / n, 4)
            agg[f"precision_article@{k}"] = round(sum(r["metrics"][f"precision_article@{k}"] for r in results_subset) / n, 4)
        agg["mrr_chunk"] = round(sum(r["metrics"]["mrr_chunk"] for r in results_subset) / n, 4)
        agg["mrr_article"] = round(sum(r["metrics"]["mrr_article"] for r in results_subset) / n, 4)
        return agg

    overall_metrics = aggregate_metrics(answerable_results)

    # Phân rã theo category
    categories = [
        "single_article",
        "single_doc_multi_chunk",
        "multi_document",
        "cross_reference",
        "complex_conditions",
        "insufficient_evidence",
        "out_of_scope",
    ]
    category_breakdown: Dict[str, Any] = {}

    for cat in categories:
        subset = [r for r in per_question_results if r["category"] == cat]
        if not subset:
            continue
        if cat in ("insufficient_evidence", "out_of_scope"):
            max_scores = [r["metrics"]["max_score"] for r in subset]
            avg_scores = [r["metrics"]["avg_top5_score"] for r in subset]
            false_alarms = sum(1 for r in subset if r["metrics"]["high_confidence_false_alarm"])
            category_breakdown[cat] = {
                "count": len(subset),
                "type": "refusal",
                "max_score_stats": calculate_percentiles(max_scores),
                "avg_top5_score_stats": calculate_percentiles(avg_scores),
                "high_confidence_false_positive_rate": round(false_alarms / len(subset), 4),
            }
        else:
            cat_agg = aggregate_metrics(subset)
            cat_agg["count"] = len(subset)
            cat_agg["type"] = "answerable"
            category_breakdown[cat] = cat_agg

    latency_stats = {
        "embedding_latency_ms": calculate_percentiles(embedding_latencies),
        "vector_search_latency_ms": calculate_percentiles(vector_search_latencies),
        "total_latency_ms": calculate_percentiles(total_latencies),
    }

    final_payload = {
        "evaluation_name": "Traditional Dense Retrieval Baseline Evaluation (RAG-09)",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "benchmark_file": "evaluation/dataset/legal_qa.json",
        "total_questions": len(benchmark),
        "answerable_questions": len(answerable_results),
        "refusal_questions": len(refusal_results),
        "overall_metrics": overall_metrics,
        "category_breakdown": category_breakdown,
        "latency_stats": latency_stats,
        "failure_count": len(failure_cases),
        "failure_cases_sample_count": min(len(failure_cases), 30),
        "failure_cases": failure_cases[:30],  # Lưu tối thiểu 20+ ca lỗi chi tiết
        "detailed_results": per_question_results,
    }

    logger.info(f"Saving detailed results to: {results_output_path}")
    with open(results_output_path, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    logger.info("Evaluation completed successfully.")
    return final_payload


if __name__ == "__main__":
    results = run_evaluation()
    print("\n" + "=" * 60)
    print("TRADITIONAL DENSE RETRIEVAL EVALUATION COMPLETED")
    print("=" * 60)
    overall = results["overall_metrics"]
    print(f"Evaluated Questions: {results['total_questions']} (Answerable: {results['answerable_questions']})")
    print(f"Recall@1 (Chunk):    {overall.get('recall_chunk@1')}")
    print(f"Recall@3 (Chunk):    {overall.get('recall_chunk@3')}")
    print(f"Recall@5 (Chunk):    {overall.get('recall_chunk@5')}")
    print(f"Recall@10 (Chunk):   {overall.get('recall_chunk@10')}")
    print(f"Recall@5 (Article):  {overall.get('recall_article@5')}")
    print(f"Hit Rate@1:          {overall.get('hit_rate@1')}")
    print(f"Hit Rate@5:          {overall.get('hit_rate@5')}")
    print(f"Hit Rate@10:         {overall.get('hit_rate@10')}")
    print(f"MRR (Chunk):         {overall.get('mrr_chunk')}")
    print(f"MRR (Article):       {overall.get('mrr_article')}")
    print(f"Precision@5 (Chunk): {overall.get('precision_chunk@5')}")
    lat = results["latency_stats"]["total_latency_ms"]
    print(f"Latency Median:      {lat['median']} ms")
    print(f"Latency P95:         {lat['p95']} ms")
    print(f"Total Failure Cases: {results['failure_count']}")
    print("=" * 60)
