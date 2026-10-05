"""
crag_runner.py - Thực thi đánh giá toàn bộ Corrective RAG (CRAG) trên benchmark RAG-08.
Đối chiếu trực tiếp với Traditional RAG Baseline trên cùng 80 câu hỏi kiểm định.
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
from CRAG.pipeline.crag_pipeline import CRAGPipeline
from CRAG.pipeline.schema import CRAGResponse
from evaluation.answer_evaluator.evaluator import LegalAnswerEvaluator
from evaluation.answer_evaluator.schema import SingleEvaluationRecord
from evaluation.runner.baseline_runner import calculate_percentiles

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("crag_runner")


class CRAGRunner:
    """Runner điều phối thực thi đánh giá toàn diện CRAG trên tập benchmark 80 câu hỏi."""

    def __init__(
        self,
        benchmark_path: Optional[Path] = None,
        crag_config: Optional[CRAGConfig] = None,
        pipeline_config: Optional[PipelineConfig] = None,
    ):
        self.root_dir = project_root
        self.benchmark_path = benchmark_path or (
            self.root_dir / "evaluation" / "dataset" / "legal_qa.json"
        )
        self.evaluator = LegalAnswerEvaluator()

        p_cfg = pipeline_config or PipelineConfig(
            TOP_K=5,
            SIMILARITY_THRESHOLD=0.45,
            LLM_PROVIDER="mock",
            TEMPERATURE=0.0,
            ENABLE_PRE_GUARD=False,
            ENABLE_POST_GUARD=True,
        )
        c_cfg = crag_config or CRAGConfig(
            UPPER_THRESHOLD=0.68,
            LOWER_THRESHOLD=0.45,
            STRIP_THRESHOLD=0.50,
            SEARCH_PROVIDER="mock",
        )

        self.pipeline = CRAGPipeline(
            pipeline_config=p_cfg,
            crag_cfg=c_cfg,
        )

    def run_benchmark(self) -> Dict[str, Any]:
        logger.info(f"Nạp benchmark từ: {self.benchmark_path}")
        with open(self.benchmark_path, "r", encoding="utf-8") as f:
            benchmark: List[Dict[str, Any]] = json.load(f)

        logger.info(f"Tổng số câu hỏi đánh giá CRAG: {len(benchmark)}")

        records: List[Dict[str, Any]] = []
        action_counts = {"REFINE": 0, "COMBINE_SEARCH": 0, "WEB_SEARCH": 0, "REFUSE": 0}
        total_latencies: List[float] = []
        retrieval_latencies: List[float] = []
        grading_latencies: List[float] = []
        refinement_latencies: List[float] = []
        search_latencies: List[float] = []
        generation_latencies: List[float] = []
        compression_ratios: List[float] = []

        for idx, item in enumerate(benchmark, start=1):
            qid = item["question_id"]
            q_text = item["question"]
            logger.info(f"[{idx}/{len(benchmark)}] CRAG executing {qid}: {q_text[:45]}...")

            t0 = time.perf_counter()
            crag_resp: CRAGResponse = self.pipeline.answer(q_text)
            elapsed_total = (time.perf_counter() - t0) * 1000.0

            action = crag_resp.action_taken
            action_counts[action] = action_counts.get(action, 0) + 1

            total_latencies.append(crag_resp.telemetry.total_latency or elapsed_total)
            retrieval_latencies.append(crag_resp.telemetry.retrieval_latency)
            grading_latencies.append(crag_resp.telemetry.grading_latency)
            refinement_latencies.append(crag_resp.telemetry.refinement_latency)
            search_latencies.append(crag_resp.telemetry.search_latency)
            generation_latencies.append(crag_resp.telemetry.generation_latency)

            if crag_resp.refined_context:
                compression_ratios.append(crag_resp.refined_context.compression_ratio)

            # Chuyển đổi thành RAGResponse để tương thích với LegalAnswerEvaluator
            standard_rag_resp = RAGResponse(
                question=crag_resp.question,
                answer=crag_resp.answer,
                citations=crag_resp.citations,
                retrieved_chunks=crag_resp.retrieved_chunks,
                latency=crag_resp.telemetry.total_latency or elapsed_total,
                refused=crag_resp.refused,
                refusal_reason=crag_resp.refusal_reason,
            )

            eval_record: SingleEvaluationRecord = self.evaluator.evaluate_response(
                benchmark_item=item,
                rag_response=standard_rag_resp,
            )

            rec_dict = eval_record.model_dump()
            rec_dict["crag_action"] = action
            rec_dict["crag_confidence"] = crag_resp.grading_result.overall_confidence
            rec_dict["compression_ratio"] = (
                crag_resp.refined_context.compression_ratio
                if crag_resp.refined_context
                else 0.0
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
                "actions": {
                    act: sum(1 for r in cat_recs if r["crag_action"] == act)
                    for act in ["REFINE", "COMBINE_SEARCH", "WEB_SEARCH", "REFUSE"]
                },
                "avg_compression_ratio": round(
                    statistics.mean([r["compression_ratio"] for r in cat_recs]), 4
                ) if cat_recs else 0.0,
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

        avg_compression = round(statistics.mean(compression_ratios), 4) if compression_ratios else 0.0

        summary = {
            "evaluation_system": "Corrective-RAG-v1 (CRAG)",
            "benchmark_dataset": "legal_qa.json (RAG-08)",
            "total_questions": total_q,
            "overall_metrics": {
                "answer_correctness": overall_accuracy,
                "faithfulness_rate": overall_faithfulness,
                "refusal_accuracy": overall_refusal_acc,
                "avg_compression_ratio": avg_compression,
                "action_distribution": action_counts,
                "action_percentages": {
                    k: round(v / total_q, 4) for k, v in action_counts.items()
                },
            },
            "latency": {
                "total": calculate_percentiles(total_latencies),
                "retrieval": calculate_percentiles(retrieval_latencies),
                "grading": calculate_percentiles(grading_latencies),
                "refinement": calculate_percentiles(refinement_latencies),
                "search": calculate_percentiles([s for s in search_latencies if s > 0]),
                "generation": calculate_percentiles(generation_latencies),
            },
            "category_metrics": category_metrics,
            "records": records,
        }

        return summary


def run_and_save_crag_eval():
    runner = CRAGRunner()
    results = runner.run_benchmark()

    out_dir = project_root / "evaluation" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "crag_evaluation.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"Đã lưu kết quả đánh giá CRAG vào: {out_file}")
    return results


if __name__ == "__main__":
    run_and_save_crag_eval()
