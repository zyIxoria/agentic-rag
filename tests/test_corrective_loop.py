"""test_corrective_loop.py - Kiểm thử chu trình Corrective Retrieval Loop (TASK CRAG-03 & CRAG-05).

Bắt buộc gồm 5 test cases theo yêu cầu kỹ thuật:
- TEST C01: Initial retrieval tốt -> SUFFICIENT, corrective_triggered = False, retry_count = 0.
- TEST C02: Initial retrieval không phù hợp, Retrieval lần 2 tốt -> corrective_triggered = True, retry_count = 1, final retrieval tốt hơn.
- TEST C03: Initial retrieval không phù hợp, Retrieval lần 2 vẫn không phù hợp -> retry_count = 1, không retry lần 3, trả refusal/insufficient evidence.
- TEST C04: Initial retrieval PARTIAL, Rewrite, Retrieval lần 2 tốt hơn -> corrective triggered, final answer dùng retrieval lần 2.
- TEST C05: Initial retrieval EMPTY, Rewrite, Retrieval lần 2 EMPTY -> refusal.
"""

import pytest
from unittest.mock import MagicMock
from typing import List

from RAG.retriever.schema import RetrievedChunk
from RAG.corrective.schemas import EvaluationStatus, RetrievalEvaluation, CRAGResponse
from RAG.corrective.evaluator import RetrievalEvaluator
from RAG.corrective.rewriter import QueryRewriter
from RAG.corrective.corrective_rag import CorrectiveRAGPipeline
from RAG.corrective.config import CRAGConfig
from RAG.prompts.legal_prompts import STANDARD_REFUSAL_ANSWER


def make_dummy_chunk(cid: str, content: str, score: float = 0.85) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=cid,
        content=content,
        score=score,
        distance=round(1.0 - score, 4),
        metadata={
            "document_id": "BLLD_2019",
            "document_title": "Bộ luật Lao động 2019",
            "article_number": "Điều 105",
            "title": "Thời giờ làm việc bình thường",
        },
        rank=1
    )


class TestCorrectiveLoop:
    """Tập kiểm thử 5 ca bắt buộc cho chu trình hiệu chỉnh truy vấn (Corrective Loop)."""

    def test_c01_initial_retrieval_good(self):
        """TEST C01: Initial retrieval tốt -> SUFFICIENT, không kích hoạt corrective, retry_count = 0."""
        mock_retriever = MagicMock()
        good_chunks = [make_dummy_chunk("c1", "Thời giờ làm việc bình thường không quá 08 giờ trong 01 ngày.", 0.9)]
        mock_retriever.retrieve.return_value = good_chunks

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = RetrievalEvaluation(
            status=EvaluationStatus.SUFFICIENT,
            confidence=0.95,
            relevant_chunk_ids=["c1"],
            irrelevant_chunk_ids=[],
            reason="Đã có đầy đủ căn cứ Điều 105."
        )

        mock_rewriter = MagicMock()

        pipeline = CorrectiveRAGPipeline(
            retriever=mock_retriever,
            evaluator=mock_evaluator,
            rewriter=mock_rewriter
        )

        res = pipeline.answer("Thời giờ làm việc bình thường tối đa bao nhiêu giờ trong một ngày?")

        assert res.corrective_triggered is False
        assert res.retry_count == 0
        assert res.refused is False
        assert res.rewritten_query is None
        assert mock_retriever.retrieve.call_count == 1
        assert mock_evaluator.evaluate.call_count == 1
        assert mock_rewriter.rewrite_query.call_count == 0

    def test_c02_initial_bad_second_good(self):
        """TEST C02: Initial retrieval không phù hợp, Retrieval lần 2 tốt -> corrective_triggered = True, retry_count = 1."""
        mock_retriever = MagicMock()
        bad_chunks = [make_dummy_chunk("c_bad", "Quy định về hội đồng tiền lương quốc gia.", 0.46)]
        good_chunks = [make_dummy_chunk("c_good", "Quy định về số ngày nghỉ việc riêng hưởng nguyên lương khi kết hôn là 03 ngày.", 0.92)]

        # Lần 1 trả bad_chunks, lần 2 trả good_chunks
        mock_retriever.retrieve.side_effect = [bad_chunks, good_chunks]

        mock_evaluator = MagicMock()
        eval_bad = RetrievalEvaluation(
            status=EvaluationStatus.INSUFFICIENT,
            confidence=0.85,
            relevant_chunk_ids=[],
            irrelevant_chunk_ids=["c_bad"],
            reason="Tài liệu không nói về kết hôn."
        )
        eval_good = RetrievalEvaluation(
            status=EvaluationStatus.SUFFICIENT,
            confidence=0.92,
            relevant_chunk_ids=["c_good"],
            irrelevant_chunk_ids=[],
            reason="Đã tìm thấy căn cứ nghỉ kết hôn."
        )
        mock_evaluator.evaluate.side_effect = [eval_bad, eval_good]

        mock_rewriter = MagicMock()
        mock_rewriter.rewrite_query.return_value = "Quy định về số ngày nghỉ việc riêng hưởng nguyên lương khi người lao động kết hôn"

        pipeline = CorrectiveRAGPipeline(
            retriever=mock_retriever,
            evaluator=mock_evaluator,
            rewriter=mock_rewriter
        )

        res = pipeline.answer("Nghỉ khi cưới được mấy ngày?")

        assert res.corrective_triggered is True
        assert res.retry_count == 1
        assert res.refused is False
        assert res.rewritten_query == "Quy định về số ngày nghỉ việc riêng hưởng nguyên lương khi người lao động kết hôn"
        assert res.final_evaluation.status == EvaluationStatus.SUFFICIENT
        assert mock_retriever.retrieve.call_count == 2
        assert mock_evaluator.evaluate.call_count == 2
        assert any(c.chunk_id == "c_good" for c in res.retrieved_chunks)

    def test_c03_initial_bad_second_still_bad_refuses_no_infinite_retry(self):
        """TEST C03: Initial không phù hợp, lần 2 vẫn không phù hợp -> retry_count = 1, KHÔNG retry lần 3, từ chối an toàn."""
        mock_retriever = MagicMock()
        bad_chunks_1 = [make_dummy_chunk("c_bad1", "Đoạn văn bản A", 0.46)]
        bad_chunks_2 = [make_dummy_chunk("c_bad2", "Đoạn văn bản B", 0.47)]
        mock_retriever.retrieve.side_effect = [bad_chunks_1, bad_chunks_2]

        mock_evaluator = MagicMock()
        eval_bad_1 = RetrievalEvaluation(
            status=EvaluationStatus.INSUFFICIENT,
            confidence=0.9,
            relevant_chunk_ids=[],
            irrelevant_chunk_ids=["c_bad1"],
            reason="Không có bằng chứng."
        )
        eval_bad_2 = RetrievalEvaluation(
            status=EvaluationStatus.INSUFFICIENT,
            confidence=0.9,
            relevant_chunk_ids=[],
            irrelevant_chunk_ids=["c_bad2"],
            reason="Vẫn không có bằng chứng sau khi viết lại."
        )
        mock_evaluator.evaluate.side_effect = [eval_bad_1, eval_bad_2]

        mock_rewriter = MagicMock()
        mock_rewriter.rewrite_query.return_value = "Truy vấn đã viết lại"

        pipeline = CorrectiveRAGPipeline(
            retriever=mock_retriever,
            evaluator=mock_evaluator,
            rewriter=mock_rewriter
        )

        res = pipeline.answer("Tích lũy giờ làm thêm trong 1 năm được quy định thế nào?")

        assert res.corrective_triggered is True
        assert res.retry_count == 1
        # Bắt buộc KHÔNG retry lần 3
        assert mock_retriever.retrieve.call_count == 2
        assert mock_evaluator.evaluate.call_count == 2
        # Bắt buộc từ chối dứt khoát vì không có bằng chứng
        assert res.refused is True
        assert res.answer == STANDARD_REFUSAL_ANSWER
        assert res.citations == []

    def test_c04_initial_partial_second_better(self):
        """TEST C04: Initial retrieval PARTIAL, Rewrite, Retrieval lần 2 tốt hơn -> corrective triggered, final answer dùng retrieval lần 2."""
        mock_retriever = MagicMock()
        partial_chunks = [make_dummy_chunk("c_part", "Giờ làm việc bình thường không quá 08 giờ.", 0.75)]
        better_chunks = [
            make_dummy_chunk("c_part", "Giờ làm việc bình thường không quá 08 giờ.", 0.75),
            make_dummy_chunk("c_overtime", "Giờ làm thêm không quá 50% trong 01 ngày.", 0.88)
        ]
        mock_retriever.retrieve.side_effect = [partial_chunks, better_chunks]

        mock_evaluator = MagicMock()
        eval_part = RetrievalEvaluation(
            status=EvaluationStatus.PARTIAL,
            confidence=0.55,
            relevant_chunk_ids=["c_part"],
            irrelevant_chunk_ids=[],
            reason="Mới chỉ có giờ làm việc bình thường, thiếu giờ làm thêm."
        )
        eval_better = RetrievalEvaluation(
            status=EvaluationStatus.SUFFICIENT,
            confidence=0.90,
            relevant_chunk_ids=["c_part", "c_overtime"],
            irrelevant_chunk_ids=[],
            reason="Đã có đầy đủ cả giờ bình thường và giờ làm thêm."
        )
        mock_evaluator.evaluate.side_effect = [eval_part, eval_better]

        mock_rewriter = MagicMock()
        mock_rewriter.rewrite_query.return_value = "Quy định về giờ làm việc bình thường và giờ làm thêm tối đa"

        pipeline = CorrectiveRAGPipeline(
            retriever=mock_retriever,
            evaluator=mock_evaluator,
            rewriter=mock_rewriter
        )

        res = pipeline.answer("Thời giờ làm việc và làm thêm giờ tối đa?")

        assert res.corrective_triggered is True
        assert res.retry_count == 1
        assert res.refused is False
        assert len(res.retrieved_chunks) >= 2
        assert any(c.chunk_id == "c_overtime" for c in res.retrieved_chunks)

    def test_c05_initial_empty_second_empty_refusal(self):
        """TEST C05: Initial retrieval EMPTY, Rewrite, Retrieval lần 2 EMPTY -> refusal."""
        mock_retriever = MagicMock()
        mock_retriever.retrieve.side_effect = [[], []]

        mock_evaluator = MagicMock()
        eval_empty = RetrievalEvaluation(
            status=EvaluationStatus.INSUFFICIENT,
            confidence=1.0,
            relevant_chunk_ids=[],
            irrelevant_chunk_ids=[],
            reason="Tập tài liệu thu hồi rỗng."
        )
        mock_evaluator.evaluate.side_effect = [eval_empty, eval_empty]

        mock_rewriter = MagicMock()
        mock_rewriter.rewrite_query.return_value = "Truy vấn không tồn tại"

        pipeline = CorrectiveRAGPipeline(
            retriever=mock_retriever,
            evaluator=mock_evaluator,
            rewriter=mock_rewriter
        )

        res = pipeline.answer("Câu hỏi không hề có trong cơ sở dữ liệu?")

        assert res.corrective_triggered is True
        assert res.retry_count == 1
        assert res.refused is True
        assert res.answer == STANDARD_REFUSAL_ANSWER
        assert res.citations == []
