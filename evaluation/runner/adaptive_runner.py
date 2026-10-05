"""
adaptive_runner.py - Thực thi đánh giá toàn bộ hệ thống Adaptive Agentic RAG trên benchmark RAG-08.
Đối chiếu trực tiếp với Traditional RAG Baseline và Corrective RAG trên cùng 80 câu hỏi kiểm định.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
import statistics
import sys
import time
from typing import Any, Dict, List, Optional

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from RAG.pipeline.config import PipelineConfig
from RAG.schemas.pipeline_schema import RAGResponse
from CRAG.config import CRAGConfig
from Adaptive_RAG.config import AdaptiveRAGConfig
from Adaptive_RAG.pipeline.adaptive_pipeline import AdaptiveRAGPipeline
from Adaptive_RAG.orchestration.schema import AdaptiveRAGResponse
from evaluation.answer_evaluator.evaluator import LegalAnswerEvaluator
from evaluation.answer_evaluator.schema import SingleEvaluationRecord
from evaluation.runner.baseline_runner import calculate_percentiles

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("adaptive_runner")


class AdaptiveRunner:
    """Runner điều phối thực thi đánh giá toàn diện Adaptive Agentic RAG trên tập benchmark 80 câu hỏi."""

    def __init__(
        self,
        benchmark_path: Optional[Path] = None,
        adaptive_cfg: Optional[AdaptiveRAGConfig] = None,
        pipeline_cfg: Optional[PipelineConfig] = None,
    ):
        self.root_dir = project_root
        self.benchmark_path = benchmark_path or (
            self.root_dir / "evaluation" / "dataset" / "legal_qa.json"
        )
        self.evaluator = LegalAnswerEvaluator()

        p_cfg = pipeline_cfg or PipelineConfig(
            TOP_K=5,
            SIMILARITY_THRESHOLD=0.45,
            LLM_PROVIDER="mock",
            TEMPERATURE=0.0,
            ENABLE_PRE_GUARD=False,
            ENABLE_POST_GUARD=True,
        )
        a_cfg = adaptive_cfg or AdaptiveRAGConfig()

        self.pipeline = AdaptiveRAGPipeline(
            config=a_cfg,
            pipeline_config=p_cfg,
        )

    def run_benchmark(self) -> Dict[str, Any]:
        logger.info(f"Nạp benchmark từ: {self.benchmark_path}")
        with open(self.benchmark_path, "r", encoding="utf-8") as f:
            benchmark: List[Dict[str, Any]] = json.load(f)

        logger.info(f"Tổng số câu hỏi đánh giá Adaptive Agentic RAG: {len(benchmark)}")

        records: List[Dict[str, Any]] = []
        route_counts = {
            "DIRECT_ANSWER": 0,
            "DIRECT_REFUSAL": 0,
            "TRADITIONAL_RAG": 0,
            "CORRECTIVE_RAG": 0,
            "DECOMPOSE_AGENTIC": 0,
        }
        total_latencies: List[float] = []
        routing_latencies: List[float] = []
        execution_latencies: List[float] = []
        synthesis_latencies: List[float] = []

        for idx, item in enumerate(benchmark, start=1):
            qid = item["question_id"]
            q_text = item["question"]
            logger.info(f"[{idx}/{len(benchmark)}] Adaptive RAG executing {qid}: {q_text[:45]}...")

            t0 = time.perf_counter()
            adapt_resp: AdaptiveRAGResponse = self.pipeline.answer(q_text)
            elapsed_total = (time.perf_counter() - t0) * 1000.0

            route_val = adapt_resp.route_taken.value
            route_counts[route_val] = route_counts.get(route_val, 0) + 1

            total_latencies.append(adapt_resp.latency_ms or elapsed_total)
            routing_latencies.append(adapt_resp.trace.routing_latency_ms)
            execution_latencies.append(adapt_resp.trace.execution_latency_ms)
            synthesis_latencies.append(adapt_resp.trace.synthesis_latency_ms)

            # Chuyển đổi thành RAGResponse để tương thích với LegalAnswerEvaluator
            standard_rag_resp = RAGResponse(
                question=adapt_resp.question,
                answer=adapt_resp.answer,
                citations=adapt_resp.citations,
                retrieved_chunks=adapt_resp.retrieved_chunks,
                latency=adapt_resp.latency_ms or elapsed_total,
                refused=adapt_resp.refused,
                refusal_reason=adapt_resp.refusal_reason,
            )

            eval_record: SingleEvaluationRecord = self.evaluator.evaluate_response(
                benchmark_item=item,
                rag_response=standard_rag_resp,
            )

            rec_dict = eval_record.model_dump()
            rec_dict["route_taken"] = route_val
            rec_dict["intent"] = adapt_resp.classification.intent.value
            rec_dict["complexity"] = adapt_resp.classification.complexity.value
            rec_dict["sub_queries_count"] = (
                len(adapt_resp.trace.plan.sub_queries)
                if adapt_resp.trace.plan
                else 1
            )
            records.append(rec_dict)

        # Tổng hợp metrics theo từng danh mục và toàn cục
        categories = sorted(list(set(r["category"] for r in records)))
        category_metrics: Dict[str, Any] = {}

        answerable_records = [r for r in records if not r["requires_refusal"]]
        refusal_records = [r for r in records if r["requires_refusal"]]
        n_ans = len(answerable_records)
        n_ref = len(refusal_records)

        for cat in categories:
            cat_recs = [r for r in records if r["category"] == cat]
            n_cat = len(cat_recs)
            cat_ans = [r for r in cat_recs if not r["requires_refusal"]]
            cat_ref = [r for r in cat_recs if r["requires_refusal"]]

            correct_cnt = sum(
                1 for r in cat_ans
                if r["answer_correctness"].get("status") in ["CORRECT", "PARTIALLY_CORRECT"]
            )
            faithful_cnt = sum(
                1 for r in cat_ans if r["faithfulness"].get("is_faithful")
            )
            ref_acc_cnt = sum(
                1 for r in cat_ref if r["refusal_metrics"].get("is_refusal_accurate")
            )

            cat_metrics = {
                "count": n_cat,
                "answer_correctness_rate": round(correct_cnt / len(cat_ans), 4) if cat_ans else 1.0,
                "faithfulness_rate": round(faithful_cnt / len(cat_ans), 4) if cat_ans else 1.0,
                "refusal_accuracy": round(ref_acc_cnt / len(cat_ref), 4) if cat_ref else 1.0,
                "routes": {
                    rt: sum(1 for r in cat_recs if r["route_taken"] == rt)
                    for rt in route_counts.keys()
                },
                "mean_sub_queries": round(
                    statistics.mean([r["sub_queries_count"] for r in cat_recs]), 2
                ) if cat_recs else 1.0,
            }
            category_metrics[cat] = cat_metrics

        total_q = len(records)
        correct_ans_total = sum(
            1 for r in answerable_records
            if r["answer_correctness"].get("status") in ["CORRECT", "PARTIALLY_CORRECT"]
        )
        faithful_total = sum(
            1 for r in answerable_records if r["faithfulness"].get("is_faithful")
        )
        refusal_acc_total = sum(
            1 for r in refusal_records if r["refusal_metrics"].get("is_refusal_accurate")
        )

        overall_accuracy = round(correct_ans_total / n_ans, 4) if n_ans else 0.0
        overall_faithfulness = round(faithful_total / n_ans, 4) if n_ans else 0.0
        overall_refusal_acc = round(refusal_acc_total / n_ref, 4) if n_ref else 0.0

        summary = {
            "evaluation_system": "Adaptive-Agentic-RAG-v1",
            "benchmark_dataset": "legal_qa.json (RAG-08)",
            "total_questions": total_q,
            "overall_metrics": {
                "answer_correctness": overall_accuracy,
                "faithfulness_rate": overall_faithfulness,
                "refusal_accuracy": overall_refusal_acc,
                "route_distribution": route_counts,
                "route_percentages": {
                    k: round(v / total_q, 4) for k, v in route_counts.items()
                },
            },
            "latency": {
                "total": calculate_percentiles(total_latencies),
                "routing": calculate_percentiles(routing_latencies),
                "execution": calculate_percentiles([e for e in execution_latencies if e > 0]),
                "synthesis": calculate_percentiles([s for s in synthesis_latencies if s > 0]),
            },
            "category_metrics": category_metrics,
            "records": records,
        }

        return summary


def run_and_save_adaptive_eval():
    runner = AdaptiveRunner()
    results = runner.run_benchmark()

    out_dir = project_root / "evaluation" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "adaptive_evaluation.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"Đã lưu kết quả đánh giá Adaptive Agentic RAG vào: {out_file}")
    return results


if __name__ == "__main__":
    run_and_save_adaptive_eval()
