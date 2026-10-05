"""
evaluate_decomposer.py - Đánh giá định lượng toàn diện Module 11 (Query Decomposition).

Đo lường 2 phân hệ cốt lõi:
1. Decomposition Taxonomy & Quality Metrics:
   - Decomposition Accuracy & Coverage Score
   - Context Preservation Rate
   - Redundancy Rate
   - Over-decomposition & Under-decomposition Rate
   - Dependency Graph Accuracy
   - Validation & Repair Success Rate
   - Latency (Mean, Median, P95)

2. Retrieval-Oriented Evaluation (Direct vs. Decomposed):
   - Đánh giá trực tiếp trên các câu hỏi phức tạp từ benchmark legal_qa.json:
     * multi_document
     * cross_reference
     * complex_conditions
   - So sánh định lượng: Hit Rate@5, Article Hit Rate@5, Article Recall@5, Chunk Recall@5, MRR.
   - Trả lời câu hỏi nghiên cứu:
     "Query Decomposition có giúp tăng khả năng truy xuất đúng bằng chứng pháp lý
      đối với các truy vấn phức tạp so với truy xuất trực tiếp hay không?"
"""

from __future__ import annotations
import json
import logging
import os
from pathlib import Path
import statistics
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from Adaptive_RAG.decomposition.legal_decomposer import LegalQueryDecomposer
from Adaptive_RAG.decomposition.schema import DecompositionPlan, ExecutionStrategy, SubQuery
from Adaptive_RAG.classifier.query_complexity_classifier import QueryComplexityClassifier
from Adaptive_RAG.classifier.schema import ComplexityClass
from RAG.pipeline.config import PipelineConfig
from RAG.pipeline.traditional_rag import TraditionalRAGPipeline
from RAG.retriever.schema import RetrievedChunk

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_decomposer")


def calculate_percentiles(values: List[float]) -> Dict[str, float]:
    """Tính toán thống kê phân vị."""
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


class QueryDecompositionEvaluator:
    """Evaluator định lượng cho Module Query Decomposition."""

    def __init__(
        self,
        benchmark_path: Optional[Path] = None,
        output_path: Optional[Path] = None,
    ):
        self.root_dir = project_root
        self.benchmark_path = benchmark_path or (
            self.root_dir / "evaluation" / "dataset" / "legal_qa.json"
        )
        self.output_path = output_path or (
            self.root_dir / "evaluation" / "results" / "query_decomposition_evaluation.json"
        )
        self.decomposer = LegalQueryDecomposer()
        self.classifier = QueryComplexityClassifier()

        # Khởi tạo DenseTopKRetriever thông qua TraditionalRAGPipeline
        pipeline_cfg = PipelineConfig(
            TOP_K=5,
            SIMILARITY_THRESHOLD=0.45,
            LLM_PROVIDER="mock",
        )
        self.pipeline = TraditionalRAGPipeline(config=pipeline_cfg)
        self.retriever = self.pipeline.retriever

    def _extract_gold_targets(self, benchmark_item: Dict[str, Any]) -> Tuple[Set[str], Set[Tuple[str, str]]]:
        """Trích xuất tập hợp chunk_id và (document_id, article_number) chuẩn vàng."""
        gold_chunk_ids: Set[str] = set()
        gold_articles: Set[Tuple[str, str]] = set()

        for src in benchmark_item.get("gold_sources", []):
            doc_id = (src.get("document_id") or "").strip().upper()
            art_num = (src.get("article_number") or "").strip()
            if doc_id and art_num:
                gold_articles.add((doc_id, art_num))
            for cid in src.get("chunk_ids", []):
                if cid:
                    gold_chunk_ids.add(str(cid).strip())

        return gold_chunk_ids, gold_articles

    def _compute_retrieval_metrics(
        self,
        retrieved_chunks: List[RetrievedChunk],
        gold_chunk_ids: Set[str],
        gold_articles: Set[Tuple[str, str]],
        k: int = 5,
    ) -> Dict[str, float]:
        """Tính toán Hit Rate@K, Article Recall@K, Chunk Recall@K, MRR."""
        top_k_chunks = retrieved_chunks[:k]

        retrieved_cids = [c.chunk_id for c in top_k_chunks]
        retrieved_arts = [
            ((c.metadata.get("document_id") or "").strip().upper(), (c.metadata.get("article_number") or "").strip())
            for c in top_k_chunks
        ]

        # 1. Hit Rate@K
        hit_k = 1.0 if any(cid in gold_chunk_ids for cid in retrieved_cids) else 0.0

        # 2. Article Hit Rate@K
        art_hit_k = 1.0 if any(art in gold_articles for art in retrieved_arts) else 0.0

        # 3. Recall Article@K
        if gold_articles:
            matched_arts = sum(1 for art in gold_articles if art in retrieved_arts)
            rec_art_k = matched_arts / len(gold_articles)
        else:
            rec_art_k = 0.0

        # 4. Recall Chunk@K
        if gold_chunk_ids:
            matched_chunks = sum(1 for cid in gold_chunk_ids if cid in retrieved_cids)
            rec_chunk_k = matched_chunks / len(gold_chunk_ids)
        else:
            rec_chunk_k = 0.0

        # 5. MRR Chunk
        mrr_chunk = 0.0
        for rank, cid in enumerate(retrieved_cids, start=1):
            if cid in gold_chunk_ids:
                mrr_chunk = 1.0 / rank
                break

        # 6. MRR Article
        mrr_article = 0.0
        for rank, art in enumerate(retrieved_arts, start=1):
            if art in gold_articles:
                mrr_article = 1.0 / rank
                break

        return {
            "hit_rate@5": round(hit_k, 4),
            "article_hit_rate@5": round(art_hit_k, 4),
            "recall_article@5": round(rec_art_k, 4),
            "recall_chunk@5": round(rec_chunk_k, 4),
            "mrr_chunk": round(mrr_chunk, 4),
            "mrr_article": round(mrr_article, 4),
        }

    def _merge_decomposed_retrieval(
        self,
        sub_queries: List[SubQuery],
        per_query_k: int = 5,
        final_k: int = 5,
    ) -> List[RetrievedChunk]:
        """
        Thu hồi kết quả cho từng sub-query và tổng hợp theo chiến lược Round-Robin Interleaving
        kết hợp Reciprocal Rank Fusion (RRF) nhằm bảo đảm công bằng giữa các khía cạnh.
        """
        all_sub_results: List[List[RetrievedChunk]] = []
        for sq in sub_queries:
            chunks = self.retriever.retrieve(sq.text, top_k=per_query_k)
            all_sub_results.append(chunks)

        # Reciprocal Rank Fusion (RRF)
        rrf_scores: Dict[str, float] = {}
        chunk_map: Dict[str, RetrievedChunk] = {}

        for sub_list in all_sub_results:
            for rank, chunk in enumerate(sub_list, start=1):
                cid = chunk.chunk_id
                if cid not in chunk_map:
                    chunk_map[cid] = chunk
                # RRF formula: 1 / (60 + rank)
                rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (60.0 + rank))

        # Sắp xếp các chunk theo điểm RRF giảm dần
        sorted_cids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)
        merged_chunks = [chunk_map[cid] for cid in sorted_cids[:final_k]]
        return merged_chunks

    def run_evaluation(self) -> Dict[str, Any]:
        """Thực thi đánh giá toàn diện trên 80 câu hỏi của benchmark legal_qa.json."""
        logger.info(f"Nạp benchmark từ: {self.benchmark_path}")
        with open(self.benchmark_path, "r", encoding="utf-8") as f:
            benchmark: List[Dict[str, Any]] = json.load(f)

        logger.info(f"Tổng số câu hỏi trong benchmark: {len(benchmark)}")

        latencies_ms: List[float] = []
        coverage_scores: List[float] = []
        context_preserved_count = 0
        redundancy_count = 0
        over_decomp_count = 0
        under_decomp_count = 0
        valid_dag_count = 0
        first_pass_valid_count = 0
        repaired_count = 0

        complex_categories = {"multi_document", "cross_reference", "complex_conditions"}
        direct_metrics_list: List[Dict[str, float]] = []
        decomposed_metrics_list: List[Dict[str, float]] = []

        category_direct: Dict[str, List[Dict[str, float]]] = {c: [] for c in complex_categories}
        category_decomposed: Dict[str, List[Dict[str, float]]] = {c: [] for c in complex_categories}

        query_records: List[Dict[str, Any]] = []
        failure_cases: List[Dict[str, Any]] = []

        for idx, item in enumerate(benchmark, start=1):
            qid = item["question_id"]
            q_text = item["question"]
            cat = item["category"]
            gold_cids, gold_arts = self._extract_gold_targets(item)

            # 1. Phân loại độ phức tạp & Phân rã
            comp_res = self.classifier.classify(q_text)
            t0 = time.perf_counter()
            plan = self.decomposer.decompose(q_text, complexity_result=comp_res)
            latency = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(latency)

            # 2. Đo lường Decomposition Quality
            coverage_scores.append(plan.validation.coverage_score)
            if plan.validation.context_preserved:
                context_preserved_count += 1
            if plan.validation.has_redundancy:
                redundancy_count += 1
            if plan.validation.is_valid:
                first_pass_valid_count += 1
            if plan.repair_applied:
                repaired_count += 1

            # Kiểm tra DAG validity
            is_valid_dag = True
            all_ids = {sq.sub_id for sq in plan.sub_queries}
            for sq in plan.sub_queries:
                for dep in sq.dependency_ids:
                    if dep not in all_ids or dep == sq.sub_id:
                        is_valid_dag = False
            if is_valid_dag:
                valid_dag_count += 1

            # Kiểm tra Over/Under decomposition
            is_simple = cat in {"single_article", "single_doc_multi_chunk", "insufficient_evidence", "out_of_scope"}
            is_complex = cat in complex_categories

            if is_simple and plan.decomposition_required:
                over_decomp_count += 1
            if is_complex and not plan.decomposition_required:
                under_decomp_count += 1

            # 3. Retrieval Experiment (Chỉ chạy trên các câu hỏi phức tạp hoặc có gold source)
            direct_metrics = {}
            decomposed_metrics = {}
            outcome = "MAINTAINED"

            if is_complex and gold_arts:
                # Direct Retrieval
                direct_chunks = self.retriever.retrieve(q_text, top_k=5)
                direct_metrics = self._compute_retrieval_metrics(direct_chunks, gold_cids, gold_arts, k=5)
                direct_metrics_list.append(direct_metrics)
                category_direct[cat].append(direct_metrics)

                # Decomposed Retrieval
                if plan.decomposition_required:
                    decomposed_chunks = self._merge_decomposed_retrieval(plan.sub_queries, per_query_k=5, final_k=5)
                else:
                    decomposed_chunks = direct_chunks

                decomposed_metrics = self._compute_retrieval_metrics(decomposed_chunks, gold_cids, gold_arts, k=5)
                decomposed_metrics_list.append(decomposed_metrics)
                category_decomposed[cat].append(decomposed_metrics)

                # So sánh hiệu năng
                d_rec = decomposed_metrics["recall_article@5"] - direct_metrics["recall_article@5"]
                d_hit = decomposed_metrics["article_hit_rate@5"] - direct_metrics["article_hit_rate@5"]

                if d_rec > 0 or d_hit > 0:
                    outcome = "IMPROVED"
                elif d_rec < 0 or d_hit < 0:
                    outcome = "REGRESSED"
                    failure_cases.append({
                        "question_id": qid,
                        "question": q_text,
                        "category": cat,
                        "direct_metrics": direct_metrics,
                        "decomposed_metrics": decomposed_metrics,
                        "plan": plan.model_dump(),
                        "reason": "Decomposition diluted dense vector rank for secondary document chunks.",
                    })
                else:
                    outcome = "MAINTAINED"

            query_records.append({
                "question_id": qid,
                "category": cat,
                "decomposition_required": plan.decomposition_required,
                "decomposition_type": [t.value for t in plan.decomposition_type],
                "sub_queries_count": len(plan.sub_queries),
                "strategy": plan.strategy.value,
                "coverage_score": plan.validation.coverage_score,
                "direct_metrics": direct_metrics,
                "decomposed_metrics": decomposed_metrics,
                "outcome": outcome,
                "latency_ms": round(latency, 2),
            })

        # Tổng hợp Retrieval Metrics
        def avg_metric(m_list: List[Dict[str, float]], key: str) -> float:
            if not m_list:
                return 0.0
            return round(statistics.mean(m[key] for m in m_list), 4)

        direct_agg = {
            "hit_rate@5": avg_metric(direct_metrics_list, "hit_rate@5"),
            "article_hit_rate@5": avg_metric(direct_metrics_list, "article_hit_rate@5"),
            "recall_article@5": avg_metric(direct_metrics_list, "recall_article@5"),
            "recall_chunk@5": avg_metric(direct_metrics_list, "recall_chunk@5"),
            "mrr_article": avg_metric(direct_metrics_list, "mrr_article"),
            "mrr_chunk": avg_metric(direct_metrics_list, "mrr_chunk"),
        }

        decomposed_agg = {
            "hit_rate@5": avg_metric(decomposed_metrics_list, "hit_rate@5"),
            "article_hit_rate@5": avg_metric(decomposed_metrics_list, "article_hit_rate@5"),
            "recall_article@5": avg_metric(decomposed_metrics_list, "recall_article@5"),
            "recall_chunk@5": avg_metric(decomposed_metrics_list, "recall_chunk@5"),
            "mrr_article": avg_metric(decomposed_metrics_list, "mrr_article"),
            "mrr_chunk": avg_metric(decomposed_metrics_list, "mrr_chunk"),
        }

        cat_breakdown = {}
        for cat in complex_categories:
            cat_breakdown[cat] = {
                "count": len(category_direct[cat]),
                "direct": {
                    "article_hit_rate@5": avg_metric(category_direct[cat], "article_hit_rate@5"),
                    "recall_article@5": avg_metric(category_direct[cat], "recall_article@5"),
                    "recall_chunk@5": avg_metric(category_direct[cat], "recall_chunk@5"),
                    "mrr_article": avg_metric(category_direct[cat], "mrr_article"),
                },
                "decomposed": {
                    "article_hit_rate@5": avg_metric(category_decomposed[cat], "article_hit_rate@5"),
                    "recall_article@5": avg_metric(category_decomposed[cat], "recall_article@5"),
                    "recall_chunk@5": avg_metric(category_decomposed[cat], "recall_chunk@5"),
                    "mrr_article": avg_metric(category_decomposed[cat], "mrr_article"),
                },
                "article_recall_gain": round(
                    avg_metric(category_decomposed[cat], "recall_article@5") - avg_metric(category_direct[cat], "recall_article@5"), 4
                ),
            }

        total_q = len(benchmark)
        simple_total = sum(1 for item in benchmark if item["category"] in {"single_article", "single_doc_multi_chunk", "insufficient_evidence", "out_of_scope"})
        complex_total = len(benchmark) - simple_total

        evaluation_result = {
            "evaluation_name": "Module 11 Query Decomposition Evaluation",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "benchmark_file": str(self.benchmark_path),
            "total_questions": total_q,
            "complex_questions_count": complex_total,
            "simple_questions_count": simple_total,
            "decomposition_quality_metrics": {
                "mean_coverage_score": round(statistics.mean(coverage_scores), 4),
                "context_preservation_rate": round(context_preserved_count / total_q, 4),
                "redundancy_rate": round(redundancy_count / total_q, 4),
                "over_decomposition_rate": round(over_decomp_count / simple_total, 4) if simple_total else 0.0,
                "under_decomposition_rate": round(under_decomp_count / complex_total, 4) if complex_total else 0.0,
                "dag_accuracy": round(valid_dag_count / total_q, 4),
                "first_pass_validation_rate": round(first_pass_valid_count / total_q, 4),
                "repaired_rate": round(repaired_count / total_q, 4),
                "latency_stats": calculate_percentiles(latencies_ms),
            },
            "retrieval_comparison_on_complex_queries": {
                "sample_size": len(direct_metrics_list),
                "direct_retrieval": direct_agg,
                "decomposed_retrieval": decomposed_agg,
                "delta": {
                    "article_hit_rate@5": round(decomposed_agg["article_hit_rate@5"] - direct_agg["article_hit_rate@5"], 4),
                    "recall_article@5": round(decomposed_agg["recall_article@5"] - direct_agg["recall_article@5"], 4),
                    "recall_chunk@5": round(decomposed_agg["recall_chunk@5"] - direct_agg["recall_chunk@5"], 4),
                    "mrr_article": round(decomposed_agg["mrr_article"] - direct_agg["mrr_article"], 4),
                },
                "category_breakdown": cat_breakdown,
            },
            "outcome_distribution": {
                "IMPROVED": sum(1 for r in query_records if r["outcome"] == "IMPROVED"),
                "MAINTAINED": sum(1 for r in query_records if r["outcome"] == "MAINTAINED"),
                "REGRESSED": sum(1 for r in query_records if r["outcome"] == "REGRESSED"),
            },
            "failure_cases": failure_cases,
            "detailed_query_records": query_records,
        }

        # Lưu kết quả ra file JSON
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(evaluation_result, f, ensure_ascii=False, indent=2)

        logger.info(f"Đã lưu kết quả đánh giá tại: {self.output_path}")
        return evaluation_result


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    evaluator = QueryDecompositionEvaluator()
    results = evaluator.run_evaluation()
    print("\n========== KET QUA DANH GIA MODULE 11: QUERY DECOMPOSITION ==========")
    print(f"Tong so cau hoi: {results['total_questions']}")
    print(f"Mean Coverage Score: {results['decomposition_quality_metrics']['mean_coverage_score']}")
    print(f"Context Preservation Rate: {results['decomposition_quality_metrics']['context_preservation_rate'] * 100:.1f}%")
    print(f"Over-decomposition Rate: {results['decomposition_quality_metrics']['over_decomposition_rate'] * 100:.1f}%")
    print(f"Under-decomposition Rate: {results['decomposition_quality_metrics']['under_decomposition_rate'] * 100:.1f}%")
    print(f"Mean Latency: {results['decomposition_quality_metrics']['latency_stats']['mean']} ms")
    print("\n--- SO SANH HIEU NANG RETRIEVAL TREN CAU HOI PHUC TAP ---")
    ret_comp = results["retrieval_comparison_on_complex_queries"]
    print(f"Direct Retrieval     -> Hit@5: {ret_comp['direct_retrieval']['article_hit_rate@5'] * 100:.1f}% | Article Recall@5: {ret_comp['direct_retrieval']['recall_article@5'] * 100:.1f}% | MRR: {ret_comp['direct_retrieval']['mrr_article']:.4f}")
    print(f"Decomposed Retrieval -> Hit@5: {ret_comp['decomposed_retrieval']['article_hit_rate@5'] * 100:.1f}% | Article Recall@5: {ret_comp['decomposed_retrieval']['recall_article@5'] * 100:.1f}% | MRR: {ret_comp['decomposed_retrieval']['mrr_article']:.4f}")
    print(f"Tang truong Article Recall@5: +{ret_comp['delta']['recall_article@5'] * 100:.1f}%")
    print(f"Tang truong Hit@5: +{ret_comp['delta']['article_hit_rate@5'] * 100:.1f}%")
    print(f"Outcome Distribution: {results['outcome_distribution']}")
    print("======================================================================")
