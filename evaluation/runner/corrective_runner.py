"""corrective_runner.py - Thực thi đánh giá toàn bộ Corrective RAG (CRAG) trên benchmark 80 câu hỏi RAG-08.

Tuân thủ nghiêm ngặt các nguyên tắc:
- Sử dụng cùng benchmark 80 câu hỏi của Traditional RAG (evaluation/dataset/legal_qa.json).
- Không sửa benchmark, không sửa gold answers, không đổi Dataset V2.1.
- Không thay đổi embedding model (all-MiniLM-L6-v2) hay Vector DB (ChromaDB 1,390 chunks).
- Top-K = 5.
- Đo lường và đối chiếu đầy đủ:
  + Retrieval metrics (Recall@K, Hit Rate@K, MRR, Precision@K).
  + Answer metrics (Overall Correctness, Strict Correctness, Faithfulness, Unsupported Claim Rate).
  + Citation metrics (Coverage, Accuracy, Precision, Invalid Citation Rate).
  + Safety / Refusal metrics (Refusal Accuracy, False Answer Rate, False Refusal Rate).
  + CRAG-specific metrics (Trigger Rate, Correction Success Rate, Recovery Rate, Unnecessary Correction Rate, Average Retries).
  + Category breakdown (A-G).
  + Latency metrics (Mean, Median, P95).
- Xuất kết quả ra:
  + evaluation/results/corrective_retrieval.json
  + evaluation/results/corrective_full_eval.json
"""

from __future__ import annotations
import json
import logging
import os
from pathlib import Path
import statistics
import sys
import time
from typing import Any, Dict, List, Set, Tuple, Optional

# Đảm bảo project root trong sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from RAG.corrective.config import CRAGConfig
from RAG.corrective.corrective_rag import CorrectiveRAGPipeline
from RAG.corrective.schemas import CRAGResponse, EvaluationStatus
from evaluation.answer_evaluator.evaluator import LegalAnswerEvaluator
from evaluation.answer_evaluator.schema import SingleEvaluationRecord
from evaluation.runner.baseline_runner import calculate_percentiles

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("corrective_runner")


class CorrectiveRAGRunner:
    """Runner điều phối thực thi đánh giá toàn diện Corrective RAG trên benchmark 80 câu hỏi."""

    def __init__(
        self,
        benchmark_path: Optional[Path] = None,
        config: Optional[CRAGConfig] = None,
    ):
        self.root_dir = project_root
        self.benchmark_path = benchmark_path or (
            self.root_dir / "evaluation" / "dataset" / "legal_qa.json"
        )
        self.evaluator = LegalAnswerEvaluator()

        crag_cfg = config or CRAGConfig(
            TOP_K=5,
            SIMILARITY_THRESHOLD=0.45,
            MAX_CORRECTIVE_RETRIES=1,
            LLM_PROVIDER="mock",
            TEMPERATURE=0.0,
            ENABLE_PRE_GUARD=True,
            ENABLE_POST_GUARD=True,
            CHROMA_PERSIST_DIRECTORY="data/chroma_db",
            COLLECTION_NAME="legal_labor_baseline_minilm"
        )
        self.pipeline = CorrectiveRAGPipeline(config=crag_cfg)

    def run_benchmark(self) -> Dict[str, Any]:
        logger.info(f"Nạp benchmark từ: {self.benchmark_path}")
        with open(self.benchmark_path, "r", encoding="utf-8") as f:
            benchmark: List[Dict[str, Any]] = json.load(f)

        logger.info(f"Tổng số câu hỏi đánh giá CRAG: {len(benchmark)}")

        records: List[SingleEvaluationRecord] = []
        crag_traces: List[Dict[str, Any]] = []

        retrieval_latencies: List[float] = []
        eval_latencies: List[float] = []
        rewrite_latencies: List[float] = []
        generation_latencies: List[float] = []
        total_latencies: List[float] = []
        latencies_no_corrective: List[float] = []
        latencies_with_corrective: List[float] = []

        # Chỉ số theo dõi Corrective
        corrective_triggered_count = 0
        total_retries = 0
        correction_success_count = 0
        recovery_count = 0
        unnecessary_correction_count = 0

        # Lưu vết retrieval cho từng câu hỏi
        per_question_retrieval: List[Dict[str, Any]] = []

        k_list = [1, 3, 5, 10]

        for idx, item in enumerate(benchmark, start=1):
            qid = item["question_id"]
            q_text = item["question"]
            cat = item["category"]
            requires_refusal = item["requires_refusal"]
            gold_sources = item.get("gold_sources", [])

            # Thu thập gold chunks và gold articles
            gold_chunk_ids: Set[str] = set()
            gold_articles: Set[Tuple[str, str]] = set()
            for gs in gold_sources:
                doc_id = gs["document_id"]
                art_num = gs.get("article_number") or ""
                gold_articles.add((doc_id, art_num))
                for cid in gs.get("chunk_ids", []):
                    gold_chunk_ids.add(cid)

            logger.info(f"[{idx}/{len(benchmark)}] CRAG executing {qid} ({cat}): {q_text[:50]}...")

            t0 = time.perf_counter()
            response: CRAGResponse = self.pipeline.answer(q_text)
            elapsed_total = (time.perf_counter() - t0) * 1000.0

            # Thu thập latencies
            total_latencies.append(response.latency_ms or elapsed_total)
            retrieval_latencies.append(response.retrieval_latency)
            eval_latencies.append(response.eval_latency)
            rewrite_latencies.append(response.rewrite_latency)
            generation_latencies.append(response.generation_latency)

            if response.corrective_triggered:
                corrective_triggered_count += 1
                total_retries += response.retry_count
                latencies_with_corrective.append(response.latency_ms or elapsed_total)
            else:
                latencies_no_corrective.append(response.latency_ms or elapsed_total)

            # Đánh giá câu trả lời qua LegalAnswerEvaluator (Dùng chung bộ đánh giá với Baseline)
            eval_record = self.evaluator.evaluate_response(
                benchmark_item=item,
                rag_response=response
            )
            records.append(eval_record)

            # =================================================================
            # Tính toán Retrieval Metrics chi tiết cho CRAG (Initial vs Final)
            # =================================================================
            init_ids = [c.chunk_id for c in response.initial_retrieval]
            init_articles = [
                (c.metadata.get("document_id", ""), c.metadata.get("article_number", "") or "")
                for c in response.initial_retrieval
            ]

            final_ids = [c.chunk_id for c in response.retrieved_chunks]
            final_articles = [
                (c.metadata.get("document_id", ""), c.metadata.get("article_number", "") or "")
                for c in response.retrieved_chunks
            ]

            q_ret_metrics: Dict[str, Any] = {
                "question_id": qid,
                "category": cat,
                "requires_refusal": requires_refusal,
                "corrective_triggered": response.corrective_triggered,
                "retry_count": response.retry_count,
                "rewritten_query": response.rewritten_query,
                "initial_status": response.initial_evaluation.status.value,
                "final_status": response.final_evaluation.status.value,
            }

            if not requires_refusal:
                # 1. Đo Initial Retrieval
                init_top5_ids = set(init_ids[:5])
                init_hit5 = 1 if (init_top5_ids & gold_chunk_ids) else 0
                init_recall5 = len(init_top5_ids & gold_chunk_ids) / len(gold_chunk_ids) if gold_chunk_ids else 0.0

                # 2. Đo Final (CRAG) Retrieval
                final_top5_ids = set(final_ids[:5])
                final_hit5 = 1 if (final_top5_ids & gold_chunk_ids) else 0
                final_recall5 = len(final_top5_ids & gold_chunk_ids) / len(gold_chunk_ids) if gold_chunk_ids else 0.0

                # MRR
                mrr_chunk = 0.0
                for rank, cid in enumerate(final_ids, start=1):
                    if cid in gold_chunk_ids:
                        mrr_chunk = 1.0 / rank
                        break

                q_ret_metrics.update({
                    "hit_rate@5": final_hit5,
                    "recall_chunk@5": round(final_recall5, 4),
                    "precision_chunk@5": round(len(final_top5_ids & gold_chunk_ids) / 5.0, 4),
                    "mrr_chunk": round(mrr_chunk, 4),
                    "initial_recall@5": round(init_recall5, 4),
                })

                # Đo lường tính hiệu quả của Corrective Loop
                if response.corrective_triggered:
                    # Recovery: Lần 1 không tìm thấy gold chunk nào (init_hit5 == 0), nhưng lần 2 tìm thấy gold chunk (final_hit5 == 1)
                    if init_hit5 == 0 and final_hit5 == 1:
                        recovery_count += 1

                    # Correction Success: Final recall hoặc hit tốt hơn Initial
                    if final_recall5 > init_recall5 or (init_hit5 == 0 and final_hit5 == 1):
                        correction_success_count += 1

                    # Unnecessary Correction: Lần 1 đã có 100% gold chunks mà vẫn kích hoạt corrective
                    if init_recall5 == 1.0:
                        unnecessary_correction_count += 1
            else:
                # Câu hỏi cần từ chối
                q_ret_metrics["refusal_accurate"] = eval_record.refusal_metrics["is_refusal_accurate"]

            per_question_retrieval.append(q_ret_metrics)

            trace_data = response.to_dict()
            trace_data["question_id"] = qid
            trace_data["category"] = cat
            crag_traces.append(trace_data)

        # =====================================================================
        # TỔNG HỢP TOÀN BỘ METRICS CỦA CORRECTIVE RAG
        # =====================================================================
        answerable_records = [r for r in records if not r.requires_refusal]
        refusal_records = [r for r in records if r.requires_refusal]

        n_ans = len(answerable_records)
        n_ref = len(refusal_records)
        total_q = len(benchmark)

        # 1. Answer Correctness
        strict_correct = sum(1 for r in answerable_records if r.answer_correctness["status"] == "CORRECT")
        partially_correct = sum(1 for r in answerable_records if r.answer_correctness["status"] == "PARTIALLY_CORRECT")
        incorrect = sum(1 for r in answerable_records if r.answer_correctness["status"] == "INCORRECT")

        # 2. Faithfulness
        faithful_count = sum(1 for r in answerable_records if r.faithfulness["is_faithful"])
        partially_faithful = sum(1 for r in answerable_records if r.faithfulness["status"] == "PARTIALLY_SUPPORTED")
        unsupported_count = sum(1 for r in answerable_records if r.faithfulness["status"] == "UNSUPPORTED")

        # 3. Citations
        has_citations = sum(1 for r in answerable_records if r.citation_metrics["has_citation"])
        avg_cit_precision = sum(r.citation_metrics["citation_precision"] for r in answerable_records) / n_ans if n_ans else 0.0
        avg_cit_accuracy = sum(r.citation_metrics["citation_accuracy"] for r in answerable_records) / n_ans if n_ans else 0.0
        avg_invalid_rate = sum(r.citation_metrics["invalid_citation_rate"] for r in answerable_records) / n_ans if n_ans else 0.0

        # 4. Refusal
        correct_refusals = sum(1 for r in refusal_records if r.refusal_metrics["is_refusal_accurate"])
        false_answers = sum(1 for r in refusal_records if r.refusal_metrics["is_false_answer"])
        false_refusals = sum(1 for r in answerable_records if r.refusal_metrics["is_false_refusal"])

        # 5. Retrieval Averages (trên câu hỏi answerable)
        ans_ret_metrics = [m for m in per_question_retrieval if not m["requires_refusal"]]
        avg_recall5 = sum(m.get("recall_chunk@5", 0.0) for m in ans_ret_metrics) / n_ans if n_ans else 0.0
        avg_hit5 = sum(m.get("hit_rate@5", 0) for m in ans_ret_metrics) / n_ans if n_ans else 0.0
        avg_mrr = sum(m.get("mrr_chunk", 0.0) for m in ans_ret_metrics) / n_ans if n_ans else 0.0
        avg_prec5 = sum(m.get("precision_chunk@5", 0.0) for m in ans_ret_metrics) / n_ans if n_ans else 0.0

        # 6. CRAG Specific Metrics
        trigger_rate = corrective_triggered_count / total_q
        correction_success_rate = (
            correction_success_count / corrective_triggered_count
            if corrective_triggered_count > 0 else 0.0
        )
        recovery_rate = (
            recovery_count / corrective_triggered_count
            if corrective_triggered_count > 0 else 0.0
        )
        unnecessary_correction_rate = unnecessary_correction_count / total_q
        avg_retry_count = total_retries / total_q

        overall_metrics = {
            # Retrieval
            "recall@5_chunk": round(avg_recall5, 4),
            "hit_rate@5": round(avg_hit5, 4),
            "mrr_chunk": round(avg_mrr, 4),
            "precision@5": round(avg_prec5, 4),
            # Answer
            "answer_correctness_rate": round((strict_correct + partially_correct) / n_ans, 4) if n_ans else 0.0,
            "strict_answer_correctness": round(strict_correct / n_ans, 4) if n_ans else 0.0,
            "faithfulness_rate": round(faithful_count / n_ans, 4) if n_ans else 0.0,
            "unsupported_claim_rate": round((partially_faithful + unsupported_count) / n_ans, 4) if n_ans else 0.0,
            # Citation
            "citation_coverage": round(has_citations / n_ans, 4) if n_ans else 0.0,
            "citation_accuracy": round(avg_cit_accuracy, 4),
            "citation_precision": round(avg_cit_precision, 4),
            "invalid_citation_rate": round(avg_invalid_rate, 4),
            # Safety
            "refusal_accuracy": round(correct_refusals / n_ref, 4) if n_ref else 0.0,
            "false_answer_rate": round(false_answers / n_ref, 4) if n_ref else 0.0,
            "false_refusal_rate": round(false_refusals / n_ans, 4) if n_ans else 0.0,
            # CRAG Specific
            "crag": {
                "corrective_trigger_rate": round(trigger_rate, 4),
                "correction_success_rate": round(correction_success_rate, 4),
                "recovery_rate": round(recovery_rate, 4),
                "unnecessary_correction_rate": round(unnecessary_correction_rate, 4),
                "average_retry_count": round(avg_retry_count, 4),
                "total_corrective_triggered": corrective_triggered_count,
                "total_retries": total_retries,
                "latency_no_corrective": calculate_percentiles(latencies_no_corrective),
                "latency_with_corrective": calculate_percentiles(latencies_with_corrective),
            },
            # Latency
            "latency": {
                "retrieval": calculate_percentiles(retrieval_latencies),
                "evaluator": calculate_percentiles(eval_latencies),
                "rewriter": calculate_percentiles(rewrite_latencies),
                "generation": calculate_percentiles(generation_latencies),
                "total": calculate_percentiles(total_latencies),
            }
        }

        # =====================================================================
        # CATEGORY BREAKDOWN (A-G)
        # =====================================================================
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
            cat_records = [r for r in records if r.category == cat]
            if not cat_records:
                continue

            c_n = len(cat_records)
            c_lat = [r.total_latency_ms for r in cat_records]

            if cat in ("insufficient_evidence", "out_of_scope"):
                c_corr_ref = sum(1 for r in cat_records if r.refusal_metrics["is_refusal_accurate"])
                c_false_ans = sum(1 for r in cat_records if r.refusal_metrics["is_false_answer"])
                category_breakdown[cat] = {
                    "count": c_n,
                    "type": "refusal",
                    "refusal_accuracy": round(c_corr_ref / c_n, 4),
                    "false_answer_rate": round(c_false_ans / c_n, 4),
                    "mean_latency_ms": round(statistics.mean(c_lat), 2),
                    "median_latency_ms": round(statistics.median(c_lat), 2),
                    "p95_latency_ms": calculate_percentiles(c_lat)["p95"],
                }
            else:
                c_corr = sum(1 for r in cat_records if r.answer_correctness["status"] in ("CORRECT", "PARTIALLY_CORRECT"))
                c_strict = sum(1 for r in cat_records if r.answer_correctness["status"] == "CORRECT")
                c_faith = sum(1 for r in cat_records if r.faithfulness["is_faithful"])
                c_unsupp = sum(1 for r in cat_records if r.faithfulness["status"] in ("PARTIALLY_SUPPORTED", "UNSUPPORTED"))
                c_cit_cov = sum(1 for r in cat_records if r.citation_metrics["has_citation"])
                c_cit_acc = sum(r.citation_metrics["citation_accuracy"] for r in cat_records) / c_n
                c_false_ref = sum(1 for r in cat_records if r.refusal_metrics["is_false_refusal"])

                category_breakdown[cat] = {
                    "count": c_n,
                    "type": "answerable",
                    "answer_correctness_rate": round(c_corr / c_n, 4),
                    "strict_correctness_rate": round(c_strict / c_n, 4),
                    "faithfulness_rate": round(c_faith / c_n, 4),
                    "unsupported_claim_rate": round(c_unsupp / c_n, 4),
                    "citation_coverage": round(c_cit_cov / c_n, 4),
                    "citation_accuracy": round(c_cit_acc, 4),
                    "false_refusal_rate": round(c_false_ref / c_n, 4),
                    "mean_latency_ms": round(statistics.mean(c_lat), 2),
                    "median_latency_ms": round(statistics.median(c_lat), 2),
                    "p95_latency_ms": calculate_percentiles(c_lat)["p95"],
                }

        # Lưu kết quả retrieval chi tiết
        results_dir = self.root_dir / "evaluation" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        retrieval_output_path = results_dir / "corrective_retrieval.json"
        with open(retrieval_output_path, "w", encoding="utf-8") as f:
            json.dump({
                "evaluation_id": "CRAG-RETRIEVAL-EVAL",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "total_questions": total_q,
                "overall_retrieval": {
                    "recall@5_chunk": overall_metrics["recall@5_chunk"],
                    "hit_rate@5": overall_metrics["hit_rate@5"],
                    "mrr_chunk": overall_metrics["mrr_chunk"],
                    "precision@5": overall_metrics["precision@5"],
                },
                "crag_metrics": overall_metrics["crag"],
                "per_question_retrieval": per_question_retrieval
            }, f, ensure_ascii=False, indent=2)

        # Lưu kết quả full evaluation
        full_eval_path = results_dir / "corrective_full_eval.json"
        full_eval_result = {
            "evaluation_id": "CRAG-FULL-EVAL",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "system_version": "Corrective-RAG-v1",
            "total_questions": total_q,
            "answerable_questions": n_ans,
            "refusal_questions": n_ref,
            "overall_metrics": overall_metrics,
            "category_breakdown": category_breakdown,
            "traces": crag_traces,
        }
        with open(full_eval_path, "w", encoding="utf-8") as f:
            json.dump(full_eval_result, f, ensure_ascii=False, indent=2)

        logger.info(f"Đã lưu kết quả tại: {retrieval_output_path} và {full_eval_path}")
        return full_eval_result


if __name__ == "__main__":
    runner = CorrectiveRAGRunner()
    res = runner.run_benchmark()
    om = res["overall_metrics"]
    print("\n" + "=" * 60)
    print("CORRECTIVE RAG (CRAG) EVALUATION FINISHED")
    print("=" * 60)
    print(f"Recall@5 (Chunk):          {om['recall@5_chunk']}")
    print(f"Hit Rate@5:                {om['hit_rate@5']}")
    print(f"MRR:                       {om['mrr_chunk']}")
    print(f"Answer Correctness Rate:   {om['answer_correctness_rate']}")
    print(f"Strict Correctness:        {om['strict_answer_correctness']}")
    print(f"Faithfulness Rate:         {om['faithfulness_rate']}")
    print(f"Unsupported Claim Rate:    {om['unsupported_claim_rate']}")
    print(f"Citation Accuracy:         {om['citation_accuracy']}")
    print(f"Citation Coverage:         {om['citation_coverage']}")
    print(f"Refusal Accuracy:          {om['refusal_accuracy']}")
    print(f"False Answer Rate:         {om['false_answer_rate']}")
    print(f"False Refusal Rate:        {om['false_refusal_rate']}")
    print(f"Corrective Trigger Rate:   {om['crag']['corrective_trigger_rate']}")
    print(f"Correction Success Rate:   {om['crag']['correction_success_rate']}")
    print(f"Recovery Rate:             {om['crag']['recovery_rate']}")
    print(f"Unnecessary Correction:    {om['crag']['unnecessary_correction_rate']}")
    print(f"Average Retry Count:       {om['crag']['average_retry_count']}")
    print(f"Mean Latency:              {om['latency']['total']['mean']} ms")
    print(f"Median Latency:            {om['latency']['total']['median']} ms")
    print(f"P95 Latency:               {om['latency']['total']['p95']} ms")
    print("=" * 60)
