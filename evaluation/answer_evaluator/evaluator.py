"""evaluator.py - Bộ đánh giá toàn diện câu trả lời của Traditional RAG."""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from evaluation.answer_evaluator.schema import SingleEvaluationRecord
from evaluation.metrics.answer_metrics import evaluate_answer_correctness
from evaluation.metrics.faithfulness_metrics import evaluate_faithfulness
from evaluation.metrics.citation_metrics import evaluate_citations
from evaluation.metrics.refusal_metrics import evaluate_refusal
from RAG.schemas.pipeline_schema import RAGResponse


class LegalAnswerEvaluator:
    """Bộ đánh giá toàn diện kết quả câu trả lời của Traditional RAG Baseline."""

    def evaluate_response(
        self,
        benchmark_item: Dict[str, Any],
        rag_response: RAGResponse,
    ) -> SingleEvaluationRecord:
        """Đánh giá một phản hồi RAG đối chiếu với câu hỏi chuẩn từ benchmark.
        
        Args:
            benchmark_item: Bản ghi từ legal_qa.json (chứa question_id, question, category, gold_sources, reference_answer, requires_refusal).
            rag_response: Đối tượng RAGResponse thu được từ pipeline.answer().
            
        Returns:
            SingleEvaluationRecord chứa toàn bộ metrics chi tiết.
        """
        qid = benchmark_item["question_id"]
        q_text = benchmark_item["question"]
        category = benchmark_item["category"]
        requires_refusal = benchmark_item["requires_refusal"]
        reference_answer = benchmark_item.get("reference_answer", "")
        gold_sources = benchmark_item.get("gold_sources", [])

        # Thu thập danh sách ID và Điều luật vàng
        gold_chunk_ids = [
            cid for gs in gold_sources for cid in gs.get("chunk_ids", [])
        ]
        gold_articles = [
            f"{gs.get('document_id', '')}:{gs.get('article_number', '')}"
            for gs in gold_sources
        ]

        retrieved_chunk_ids = [c.chunk_id for c in rag_response.retrieved_chunks]

        # 1. Đánh giá Answer Correctness
        correctness_res = evaluate_answer_correctness(
            generated_answer=rag_response.answer,
            reference_answer=reference_answer,
            gold_sources=gold_sources,
            refused=rag_response.refused,
            requires_refusal=requires_refusal,
            citations=rag_response.citations,
        )

        # 2. Đánh giá Faithfulness
        faithfulness_res = evaluate_faithfulness(
            generated_answer=rag_response.answer,
            retrieved_chunks=rag_response.retrieved_chunks,
            refused=rag_response.refused,
        )

        # 3. Đánh giá Citations
        citation_res = evaluate_citations(
            citations=rag_response.citations,
            retrieved_chunks=rag_response.retrieved_chunks,
            gold_sources=gold_sources,
            refused=rag_response.refused,
            requires_refusal=requires_refusal,
        )

        # 4. Đánh giá Refusal
        refusal_res = evaluate_refusal(
            refused=rag_response.refused,
            requires_refusal=requires_refusal,
            refusal_reason=rag_response.refusal_reason or "",
        )

        # 5. Phân loại lỗi (Error Classification)
        error_type: Optional[str] = None
        error_details: Optional[str] = None

        if requires_refusal and not rag_response.refused:
            error_type = "REFUSAL_ERROR"
            error_details = "Câu hỏi ngoài phạm vi hoặc thiếu chứng cứ nhưng hệ thống không từ chối (False Answer)."
        elif not requires_refusal and rag_response.refused:
            error_type = "REFUSAL_ERROR"
            error_details = f"Từ chối nhầm câu hỏi hợp lệ (False Refusal) do: {rag_response.refusal_reason}"
        elif correctness_res["status"] == "INCORRECT":
            # Kiểm tra nguyên nhân do retrieval hay do generation
            retrieved_gold = set(retrieved_chunk_ids) & set(gold_chunk_ids)
            if not retrieved_gold:
                error_type = "RETRIEVAL_ERROR"
                error_details = "Retriever không thu hồi được bất kỳ chunk vàng nào trong Top-K."
            else:
                error_type = "GENERATION_ERROR"
                error_details = "Retriever có thu hồi được chunk vàng nhưng Generator sinh sai hoặc bỏ sót kết luận."
        elif citation_res["invalid_citation_rate"] > 0:
            error_type = "CITATION_ERROR"
            error_details = f"Có {citation_res['invalid_citations']} trích dẫn không hợp lệ hoặc không có trong ngữ cảnh."
        elif not faithfulness_res["is_faithful"]:
            error_type = "GENERATION_ERROR"
            error_details = "Câu trả lời chứa khẳng định không được bảo chứng bởi ngữ cảnh thu hồi (Ungrounded Claim)."

        # Ước tính token cho local/mock generator
        words_in = len(q_text.split()) + sum(len(c.content.split()) for c in rag_response.retrieved_chunks)
        words_out = len(rag_response.answer.split())
        approx_input_tokens = int(words_in * 1.3)
        approx_output_tokens = int(words_out * 1.3)

        return SingleEvaluationRecord(
            question_id=qid,
            question=q_text,
            category=category,
            requires_refusal=requires_refusal,
            refused=rag_response.refused,
            refusal_reason=rag_response.refusal_reason,
            generated_answer=rag_response.answer,
            reference_answer=reference_answer,
            citations=rag_response.citations,
            retrieved_chunk_ids=retrieved_chunk_ids,
            gold_chunk_ids=gold_chunk_ids,
            gold_articles=gold_articles,
            answer_correctness=correctness_res,
            faithfulness=faithfulness_res,
            citation_metrics=citation_res,
            refusal_metrics=refusal_res,
            retrieval_latency_ms=rag_response.retrieval_latency or 0.0,
            context_latency_ms=rag_response.context_latency or 0.0,
            generation_latency_ms=rag_response.generation_latency or 0.0,
            citation_latency_ms=rag_response.citation_latency or 0.0,
            total_latency_ms=rag_response.latency or 0.0,
            input_tokens=approx_input_tokens,
            output_tokens=approx_output_tokens,
            total_tokens=approx_input_tokens + approx_output_tokens,
            error_type=error_type,
            error_details=error_details,
        )
