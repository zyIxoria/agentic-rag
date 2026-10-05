"""test_corrective_evaluator.py - Bộ kiểm thử đơn vị cho Retrieval Evaluator (TASK CRAG-01 & CRAG-05).

Kiểm thử toàn diện 9 trường hợp bắt buộc:
1. Relevant retrieval -> SUFFICIENT
2. Partially relevant retrieval -> PARTIAL
3. Irrelevant retrieval -> INSUFFICIENT
4. Empty retrieval -> INSUFFICIENT
5. Mixed relevant/irrelevant -> đánh giá đúng theo schema
6. Invalid evaluator output -> phải được validate
7. Confidence < 0 -> reject
8. Confidence > 1 -> reject
9. Unknown status -> reject
"""

import pytest
from typing import List

from RAG.retriever.schema import RetrievedChunk
from RAG.corrective.schemas import EvaluationStatus, RetrievalEvaluation
from RAG.corrective.evaluator import RetrievalEvaluator
from RAG.corrective.config import CRAGConfig


def create_dummy_chunk(chunk_id: str, content: str, score: float = 0.85, doc_id: str = "BLLD_2019") -> RetrievedChunk:
    """Helper tạo RetrievedChunk giả lập phục vụ kiểm thử."""
    return RetrievedChunk(
        chunk_id=chunk_id,
        content=content,
        score=score,
        distance=round(1.0 - score, 4),
        metadata={
            "document_id": doc_id,
            "document_title": "Bộ luật Lao động 2019",
            "article_number": "Điều 105",
            "title": "Thời giờ làm việc bình thường",
        },
        rank=1
    )


class TestCorrectiveEvaluator:
    """Tập kiểm thử đơn vị cho Retrieval Evaluator theo đặc tả kỹ thuật CRAG."""

    @pytest.fixture
    def evaluator(self) -> RetrievalEvaluator:
        config = CRAGConfig(
            SIMILARITY_THRESHOLD=0.45,
            EVALUATOR_SUFFICIENT_THRESHOLD=0.65,
            EVALUATOR_PARTIAL_THRESHOLD=0.35,
        )
        return RetrievalEvaluator(config=config)

    def test_01_relevant_retrieval_sufficient(self, evaluator: RetrievalEvaluator):
        """TEST 1: Relevant retrieval -> SUFFICIENT."""
        query = "Thời giờ làm việc bình thường của người lao động tối đa bao nhiêu giờ trong một ngày?"
        chunks = [
            create_dummy_chunk(
                chunk_id="chunk_art105_1",
                content="Thời giờ làm việc bình thường không quá 08 giờ trong 01 ngày và không quá 48 giờ trong 01 tuần.",
                score=0.92
            ),
            create_dummy_chunk(
                chunk_id="chunk_art105_2",
                content="Người sử dụng lao động có quyền quy định thời giờ làm việc theo giờ hoặc ngày hoặc tuần.",
                score=0.88
            )
        ]

        result = evaluator.evaluate(query, chunks)

        assert result.status == EvaluationStatus.SUFFICIENT
        assert 0.0 <= result.confidence <= 1.0
        assert "chunk_art105_1" in result.relevant_chunk_ids
        assert len(result.relevant_chunk_ids) >= 1
        assert len(result.reason) > 0

    def test_02_partially_relevant_retrieval_partial(self, evaluator: RetrievalEvaluator):
        """TEST 2: Partially relevant retrieval -> PARTIAL."""
        # Câu hỏi kép về cả giờ làm việc bình thường và giờ làm thêm tối đa
        query = "Thời giờ làm việc bình thường tối đa bao nhiêu giờ trong một ngày và số giờ làm thêm tối đa là bao nhiêu?"
        chunks = [
            create_dummy_chunk(
                chunk_id="chunk_art105_only",
                content="Thời giờ làm việc bình thường không quá 08 giờ trong 01 ngày và không quá 48 giờ trong 01 tuần.",
                score=0.75
            ),
            create_dummy_chunk(
                chunk_id="chunk_noise",
                content="Trang bị phương tiện bảo hộ cá nhân khi làm việc trong điều kiện nguy hiểm độc hại.",
                score=0.30
            )
        ]

        result = evaluator.evaluate(query, chunks)

        assert result.status == EvaluationStatus.PARTIAL
        assert 0.0 <= result.confidence <= 1.0
        assert "chunk_art105_only" in result.relevant_chunk_ids
        assert "chunk_noise" in result.irrelevant_chunk_ids

    def test_03_irrelevant_retrieval_insufficient(self, evaluator: RetrievalEvaluator):
        """TEST 3: Irrelevant retrieval (distractor with high similarity or wrong topic) -> INSUFFICIENT."""
        # Case câu hỏi hỏi về tích lũy giờ làm thêm (không có bằng chứng trong luật)
        query = "Tích lũy giờ làm thêm trong 1 năm được quy định thế nào?"
        chunks = [
            create_dummy_chunk(
                chunk_id="chunk_art107_distractor",
                content="Làm thêm giờ là khoảng thời gian làm việc ngoài thời giờ làm việc bình thường. Bảo đảm số giờ làm thêm không quá 50% số giờ làm việc bình thường trong 01 ngày.",
                score=0.85
            )
        ]

        result = evaluator.evaluate(query, chunks)

        # Evaluator phải nhận diện được similarity cao != sufficient evidence vì thiếu điều kiện tích lũy
        assert result.status == EvaluationStatus.INSUFFICIENT
        assert result.confidence >= 0.70
        assert "chunk_art107_distractor" in result.irrelevant_chunk_ids
        assert len(result.relevant_chunk_ids) == 0

    def test_04_empty_retrieval_insufficient(self, evaluator: RetrievalEvaluator):
        """TEST 4: Empty retrieval -> INSUFFICIENT."""
        query = "Quy định về sa thải người lao động?"
        empty_chunks: List[RetrievedChunk] = []

        result = evaluator.evaluate(query, empty_chunks)

        assert result.status == EvaluationStatus.INSUFFICIENT
        assert result.confidence == 1.0
        assert result.relevant_chunk_ids == []
        assert result.irrelevant_chunk_ids == []
        assert "rỗng" in result.reason.lower()

    def test_05_mixed_relevant_irrelevant(self, evaluator: RetrievalEvaluator):
        """TEST 5: Mixed relevant/irrelevant -> đánh giá đúng theo schema và disjoint IDs."""
        query = "Quy định về thời gian thử việc tối đa đối với người lao động?"
        chunks = [
            create_dummy_chunk(
                chunk_id="chunk_probation",
                content="Thời gian thử việc do hai bên thỏa thuận nhưng chỉ được thử việc một lần và không quá 180 ngày đối với công việc quản lý doanh nghiệp.",
                score=0.90
            ),
            create_dummy_chunk(
                chunk_id="chunk_unrelated_traffic",
                content="Thẩm quyền xử phạt vi phạm hành chính của thanh tra lao động.",
                score=0.25
            )
        ]

        result = evaluator.evaluate(query, chunks)

        assert "chunk_probation" in result.relevant_chunk_ids
        assert "chunk_unrelated_traffic" in result.irrelevant_chunk_ids
        assert set(result.relevant_chunk_ids).isdisjoint(set(result.irrelevant_chunk_ids))
        assert set(result.relevant_chunk_ids) | set(result.irrelevant_chunk_ids) == {"chunk_probation", "chunk_unrelated_traffic"}

    def test_06_invalid_evaluator_output_validation(self, evaluator: RetrievalEvaluator):
        """TEST 6: Invalid evaluator output (chứa chunk ID không có trong retrieval) -> reject."""
        chunks = [create_dummy_chunk("chunk_1", "Nội dung 1")]

        bad_eval = RetrievalEvaluation(
            status=EvaluationStatus.SUFFICIENT,
            confidence=0.8,
            relevant_chunk_ids=["chunk_NON_EXISTENT"],
            irrelevant_chunk_ids=[],
            reason="Lý do giả lập"
        )

        with pytest.raises(ValueError, match="chunk ID không tồn tại"):
            evaluator.validate_evaluation(bad_eval, chunks)

    def test_07_confidence_less_than_zero_rejected(self):
        """TEST 7: Confidence < 0 -> reject."""
        with pytest.raises(ValueError, match="Confidence phải nằm trong đoạn"):
            RetrievalEvaluation(
                status=EvaluationStatus.SUFFICIENT,
                confidence=-0.1,
                relevant_chunk_ids=[],
                irrelevant_chunk_ids=[],
                reason="Lỗi âm"
            )

    def test_08_confidence_greater_than_one_rejected(self):
        """TEST 8: Confidence > 1 -> reject."""
        with pytest.raises(ValueError, match="Confidence phải nằm trong đoạn"):
            RetrievalEvaluation(
                status=EvaluationStatus.SUFFICIENT,
                confidence=1.05,
                relevant_chunk_ids=[],
                irrelevant_chunk_ids=[],
                reason="Lỗi lớn hơn 1"
            )

    def test_09_unknown_status_rejected(self):
        """TEST 9: Unknown status -> reject."""
        with pytest.raises(ValueError, match="Trạng thái đánh giá không hợp lệ"):
            RetrievalEvaluation(
                status="COMPLETELY_UNKNOWN_STATUS",  # type: ignore
                confidence=0.8,
                relevant_chunk_ids=[],
                irrelevant_chunk_ids=[],
                reason="Lỗi status"
            )
