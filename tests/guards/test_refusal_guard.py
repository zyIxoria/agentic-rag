"""test_refusal_guard.py - Bộ kiểm thử đơn vị cho Refusal Guard (TASK RAG-06).

Kiểm thử:
1. test_01_empty_retrieval_refusal
2. test_02_low_similarity_threshold_refusal
3. test_03_valid_retrieval_pass
4. test_04_post_generation_all_invalid_citations
5. test_05_post_generation_valid_citations_pass
6. test_06_standard_refusal_message
7. test_07_configurable_threshold
"""

import unittest
from RAG.retriever.schema import RetrievedChunk
from RAG.generator.schema import GenerationResult
from RAG.citation.schema import CitationResolutionResult, LegalCitation
from RAG.guards.config import GuardConfig
from RAG.guards.refusal_guard import RefusalGuard, GuardCheckResult
from RAG.prompts.legal_prompts import STANDARD_REFUSAL_ANSWER


class TestRefusalGuard(unittest.TestCase):
    """Test suite cho phân hệ Refusal Guard."""

    def setUp(self):
        self.guard = RefusalGuard(config=GuardConfig(SIMILARITY_THRESHOLD=0.45))

    def _create_mock_chunk(self, chunk_id: str, score: float, rank: int = 1) -> RetrievedChunk:
        return RetrievedChunk(
            chunk_id=chunk_id,
            content=f"Nội dung của chunk {chunk_id}",
            score=score,
            rank=rank,
            metadata={
                "document_title": "Bộ luật Lao động 2019",
                "document_number": "45/2019/QH14",
                "article_number": "Điều 1"
            }
        )

    def test_01_empty_retrieval_refusal(self):
        """Kiểm thử pre-generation guard khi danh sách thu hồi rỗng."""
        res = self.guard.check_pre_generation([])
        self.assertFalse(res.passed)
        self.assertTrue(res.trigger_refusal)
        self.assertIn("Không tìm thấy bất kỳ tài liệu pháp lý nào", res.reason)
        self.assertEqual(res.refusal_message, STANDARD_REFUSAL_ANSWER)

    def test_02_low_similarity_threshold_refusal(self):
        """Kiểm thử pre-generation guard khi điểm tương đồng thấp hơn ngưỡng 0.45."""
        low_score_chunks = [
            self._create_mock_chunk("c1", 0.35, 1),
            self._create_mock_chunk("c2", 0.28, 2),
        ]
        res = self.guard.check_pre_generation(low_score_chunks)
        self.assertFalse(res.passed)
        self.assertTrue(res.trigger_refusal)
        self.assertIn("thấp hơn ngưỡng cho phép", res.reason)

    def test_03_valid_retrieval_pass(self):
        """Kiểm thử pre-generation guard khi có chunk đạt điểm tương đồng cao."""
        valid_chunks = [
            self._create_mock_chunk("c1", 0.82, 1),
            self._create_mock_chunk("c2", 0.65, 2),
        ]
        res = self.guard.check_pre_generation(valid_chunks)
        self.assertTrue(res.passed)
        self.assertFalse(res.trigger_refusal)
        self.assertEqual(res.metrics["max_score"], 0.82)

    def test_04_post_generation_all_invalid_citations(self):
        """Kiểm thử post-generation guard khi toàn bộ trích dẫn của LLM là giả mạo (SOURCE 99)."""
        gen_res = GenerationResult(
            answer="Người lao động được nghỉ 100 ngày theo [SOURCE 99].",
            citations=["SOURCE 99"],
            refused=False,
            model_name="test-model",
            provider="test"
        )
        citation_res = CitationResolutionResult(
            original_answer=gen_res.answer,
            enriched_answer=gen_res.answer,
            valid_citations=[],
            invalid_citations=["[SOURCE 99]"],
            has_invalid_citations=True,
            citations_count=0
        )

        res = self.guard.check_post_generation(gen_res, citation_res)
        self.assertFalse(res.passed)
        self.assertTrue(res.trigger_refusal)
        self.assertIn("REJECT INVALID CITATIONS", res.reason)

    def test_05_post_generation_valid_citations_pass(self):
        """Kiểm thử post-generation guard khi câu trả lời có trích dẫn hợp lệ."""
        gen_res = GenerationResult(
            answer="Người lao động có các quyền theo [SOURCE 1].",
            citations=["SOURCE 1"],
            refused=False,
            model_name="test-model",
            provider="test"
        )
        legal_cit = LegalCitation(
            source_id="[SOURCE 1]",
            document_title="Bộ luật Lao động 2019",
            article_number="Điều 5",
            formatted_citation="[Bộ luật Lao động 2019, Điều 5]"
        )
        citation_res = CitationResolutionResult(
            original_answer=gen_res.answer,
            enriched_answer="Người lao động có các quyền theo [Bộ luật Lao động 2019, Điều 5].",
            valid_citations=[legal_cit],
            invalid_citations=[],
            has_invalid_citations=False,
            citations_count=1
        )

        res = self.guard.check_post_generation(gen_res, citation_res)
        self.assertTrue(res.passed)
        self.assertFalse(res.trigger_refusal)

    def test_06_standard_refusal_message(self):
        """Kiểm thử hàm tạo phản hồi từ chối chuẩn mực create_refusal_response."""
        reason = "Bằng chứng không đủ độ tin cậy."
        refusal_res = self.guard.create_refusal_response(reason=reason)

        self.assertTrue(refusal_res.refused)
        self.assertEqual(refusal_res.citations, [])
        self.assertEqual(refusal_res.answer, STANDARD_REFUSAL_ANSWER)
        self.assertEqual(refusal_res.reason, reason)

    def test_07_configurable_threshold(self):
        """Kiểm thử cấu hình ngưỡng tùy chỉnh."""
        strict_guard = RefusalGuard(config=GuardConfig(SIMILARITY_THRESHOLD=0.85))
        chunks = [self._create_mock_chunk("c1", 0.75, 1)]
        res = strict_guard.check_pre_generation(chunks)
        self.assertFalse(res.passed)
        self.assertTrue(res.trigger_refusal)


if __name__ == "__main__":
    unittest.main()
