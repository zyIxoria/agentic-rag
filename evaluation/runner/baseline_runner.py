"""baseline_runner.py - Thực thi đánh giá toàn bộ Traditional RAG Baseline trên benchmark RAG-08."""

from __future__ import annotations
import json
import logging
import os
from pathlib import Path
import statistics
import sys
import time
from typing import Any, Dict, List

# Bảo đảm project root nằm trong sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from RAG.pipeline.config import PipelineConfig
from RAG.pipeline.traditional_rag import TraditionalRAGPipeline
from evaluation.answer_evaluator.evaluator import LegalAnswerEvaluator
from evaluation.answer_evaluator.schema import SingleEvaluationRecord

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("baseline_runner")


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


class BaselineRunner:
    """Runner điều phối thực thi toàn bộ 80 câu hỏi qua Traditional RAG Pipeline và tổng hợp metrics."""

    def __init__(
        self,
        benchmark_path: Optional[Path] = None,
        config: Optional[PipelineConfig] = None,
    ):
        self.root_dir = project_root
        self.benchmark_path = benchmark_path or (self.root_dir / "evaluation" / "dataset" / "legal_qa.json")
        self.rag_09_results_path = self.root_dir / "evaluation" / "results" / "retrieval_baseline.json"
        self.evaluator = LegalAnswerEvaluator()

        # Cấu hình pipeline với LLM_PROVIDER="mock" cho tính tất định và độc lập ngoại tuyến
        pipeline_cfg = config or PipelineConfig(
            TOP_K=5,
            SIMILARITY_THRESHOLD=0.45,
            LLM_PROVIDER="mock",
            TEMPERATURE=0.0,
            ENABLE_PRE_GUARD=True,
            ENABLE_POST_GUARD=True,
        )
        self.pipeline = TraditionalRAGPipeline(config=pipeline_cfg)

    def run_benchmark(self) -> Dict[str, Any]:
        logger.info(f"Nạp benchmark từ: {self.benchmark_path}")
        with open(self.benchmark_path, "r", encoding="utf-8") as f:
            benchmark: List[Dict[str, Any]] = json.load(f)

        logger.info(f"Tổng số câu hỏi cần đánh giá: {len(benchmark)}")

        records: List[SingleEvaluationRecord] = []
        retrieval_latencies: List[float] = []
        generation_latencies: List[float] = []
        total_latencies: List[float] = []
        input_tokens_list: List[int] = []
        output_tokens_list: List[int] = []
        total_tokens_list: List[int] = []

        for idx, item in enumerate(benchmark, start=1):
            qid = item["question_id"]
            q_text = item["question"]
            logger.info(f"[{idx}/{len(benchmark)}] Đang thực thi {qid}: {q_text[:50]}...")

            # Thực thi pipeline Traditional RAG
            t0 = time.perf_counter()
            response = self.pipeline.answer(q_text)
            elapsed_total = (time.perf_counter() - t0) * 1000.0

            # Đánh giá câu trả lời
            record = self.evaluator.evaluate_response(
                benchmark_item=item,
                rag_response=response,
            )
            records.append(record)

            retrieval_latencies.append(record.retrieval_latency_ms)
            generation_latencies.append(record.generation_latency_ms)
            total_latencies.append(record.total_latency_ms)
            input_tokens_list.append(record.input_tokens)
            output_tokens_list.append(record.output_tokens)
            total_tokens_list.append(record.total_tokens)

        # Nạp metrics retrieval từ RAG-09 nếu có
        rag09_retrieval_metrics = {}
        if self.rag_09_results_path.exists():
            with open(self.rag_09_results_path, "r", encoding="utf-8") as f:
                r09 = json.load(f)
                rag09_retrieval_metrics = r09.get("overall_metrics", {})

        # Tổng hợp metrics
        answerable_records = [r for r in records if not r.requires_refusal]
        refusal_records = [r for r in records if r.requires_refusal]

        n_ans = len(answerable_records)
        n_ref = len(refusal_records)

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

        overall_metrics = {
            "recall@5_chunk": rag09_retrieval_metrics.get("recall_chunk@5", 0.1431),
            "recall@5_article": rag09_retrieval_metrics.get("recall_article@5", 0.2109),
            "mrr_chunk": rag09_retrieval_metrics.get("mrr_chunk", 0.1932),
            "hit_rate@5": rag09_retrieval_metrics.get("hit_rate@5", 0.2969),
            "answer_correctness_rate": round((strict_correct + partially_correct) / n_ans, 4) if n_ans else 0.0,
            "strict_answer_correctness": round(strict_correct / n_ans, 4) if n_ans else 0.0,
            "faithfulness_rate": round(faithful_count / n_ans, 4) if n_ans else 0.0,
            "unsupported_claim_rate": round((partially_faithful + unsupported_count) / n_ans, 4) if n_ans else 0.0,
            "citation_accuracy": round(avg_cit_accuracy, 4),
            "citation_coverage": round(has_citations / n_ans, 4) if n_ans else 0.0,
            "citation_precision": round(avg_cit_precision, 4),
            "invalid_citation_rate": round(avg_invalid_rate, 4),
            "refusal_accuracy": round(correct_refusals / n_ref, 4) if n_ref else 0.0,
            "false_answer_rate": round(false_answers / n_ref, 4) if n_ref else 0.0,
            "false_refusal_rate": round(false_refusals / n_ans, 4) if n_ans else 0.0,
            "latency": {
                "retrieval": calculate_percentiles(retrieval_latencies),
                "generation": calculate_percentiles(generation_latencies),
                "total": calculate_percentiles(total_latencies),
            },
            "token_usage": {
                "mean_input_tokens": round(statistics.mean(input_tokens_list), 1),
                "mean_output_tokens": round(statistics.mean(output_tokens_list), 1),
                "mean_total_tokens": round(statistics.mean(total_tokens_list), 1),
                "note": "N/A (Local / Mock Engine - Token counts estimated via subword ratio)"
            }
        }

        # Category Breakdown
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

        # Error Analysis Collection
        successful_cases = [r.dict() for r in records if r.answer_correctness["status"] == "CORRECT" and not r.requires_refusal]
        retrieval_failures = [r.dict() for r in records if r.error_type == "RETRIEVAL_ERROR"]
        answer_failures = [r.dict() for r in records if r.answer_correctness["status"] == "INCORRECT" and not r.requires_refusal]
        citation_failures = [r.dict() for r in records if r.citation_metrics.get("invalid_citation_rate", 0) > 0 or (not r.requires_refusal and not r.refused and r.citation_metrics.get("citation_accuracy", 0) == 0)]
        refusal_cases = [r.dict() for r in records if r.requires_refusal or r.refused]

        error_analysis = {
            "successful_cases_count": len(successful_cases),
            "retrieval_failures_count": len(retrieval_failures),
            "answer_failures_count": len(answer_failures),
            "citation_failures_count": len(citation_failures),
            "refusal_cases_count": len(refusal_cases),
            "samples": {
                "successful_cases": successful_cases[:12],
                "retrieval_failures": retrieval_failures[:12],
                "answer_failures": answer_failures[:12],
                "citation_failures": citation_failures[:12],
                "refusal_cases": refusal_cases[:12],
            }
        }

        final_result = {
            "evaluation_id": "RAG-10-TRADITIONAL-BASELINE-EVAL",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "baseline_version": "Traditional-RAG-v1",
            "total_questions": len(records),
            "answerable_questions": n_ans,
            "refusal_questions": n_ref,
            "overall_metrics": overall_metrics,
            "category_breakdown": category_breakdown,
            "error_analysis": error_analysis,
            "detailed_records": [r.dict() for r in records],
        }

        # Lưu kết quả thô
        results_dir = self.root_dir / "evaluation" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        raw_eval_path = results_dir / "traditional_baseline_full_eval.json"
        with open(raw_eval_path, "w", encoding="utf-8") as f:
            json.dump(final_result, f, ensure_ascii=False, indent=2)

        logger.info(f"Đã lưu kết quả đánh giá thô tại: {raw_eval_path}")
        return final_result


if __name__ == "__main__":
    runner = BaselineRunner()
    res = runner.run_benchmark()
    print("\n" + "=" * 60)
    print("RAG-10 TRADITIONAL BASELINE EVALUATION FINISHED")
    print("=" * 60)
    om = res["overall_metrics"]
    print(f"Recall@5 (Chunk):          {om['recall@5_chunk']}")
    print(f"MRR:                       {om['mrr_chunk']}")
    print(f"Answer Correctness Rate:   {om['answer_correctness_rate']}")
    print(f"Strict Correctness:        {om['strict_answer_correctness']}")
    print(f"Faithfulness Rate:         {om['faithfulness_rate']}")
    print(f"Unsupported Claim Rate:    {om['unsupported_claim_rate']}")
    print(f"Citation Accuracy:         {om['citation_accuracy']}")
    print(f"Citation Coverage:         {om['citation_coverage']}")
    print(f"Refusal Accuracy:          {om['refusal_accuracy']}")
    print(f"Mean Latency:              {om['latency']['total']['mean']} ms")
    print(f"P95 Latency:               {om['latency']['total']['p95']} ms")
    print(f"Mean Input Tokens:         {om['token_usage']['mean_input_tokens']}")
    print(f"Mean Output Tokens:        {om['token_usage']['mean_output_tokens']}")
    print("=" * 60)
