"""test_pipeline.py - Bộ kiểm thử đơn vị và tích hợp toàn chuỗi Traditional RAG Pipeline (TASK RAG-07).

Bao gồm 9 nhóm kiểm thử bắt buộc:
1. test_01_simple_legal_question
2. test_02_article_specific_question
3. test_03_multi_source_question
4. test_04_irrelevant_question
5. test_05_insufficient_evidence_refusal
6. test_06_citation_validation
7. test_07_end_to_end_failure_handling
8. test_08_no_hidden_intelligence_verification
9. test_09_latency_metrics_measurable
"""

import unittest
from unittest.mock import MagicMock, patch

from RAG.pipeline.config import PipelineConfig
from RAG.pipeline.traditional_rag import TraditionalRAGPipeline
from RAG.schemas.pipeline_schema import RAGResponse
from RAG.prompts.legal_prompts import STANDARD_REFUSAL_ANSWER


class TestTraditionalRAGPipeline(unittest.TestCase):
    """Test suite cho toàn chuỗi Traditional RAG Pipeline."""

    @classmethod
    def setUpClass(cls):
        # Khởi tạo pipeline mặc định với Mock LLM Generator để kiểm thử nhanh và độc lập mạng
        cls.config = PipelineConfig(
            TOP_K=5,
            SIMILARITY_THRESHOLD=0.45,
            LLM_PROVIDER="mock"
        )
        cls.pipeline = TraditionalRAGPipeline(config=cls.config)

    def test_01_simple_legal_question(self):
        """Kiểm thử câu hỏi pháp lý cơ bản vận hành trơn tru từ đầu đến cuối."""
        q = "Thời giờ làm việc bình thường của người lao động được quy định như thế nào?"
        res = self.pipeline.answer(q)

        self.assertIsInstance(res, RAGResponse)
        self.assertEqual(res.question, q)
        self.assertFalse(res.refused)
        self.assertTrue(len(res.answer) > 20)
        self.assertTrue(len(res.retrieved_chunks) > 0)
        self.assertTrue(len(res.citations) > 0)
        self.assertGreater(res.latency, 0.0)

    def test_02_article_specific_question(self):
        """Kiểm thử câu hỏi nhắm vào điều khoản cụ thể (Điều 125 sa thải)."""
        q = "Người sử dụng lao động có quyền sa thải người lao động trong những trường hợp nào?"
        res = self.pipeline.answer(q)

        self.assertFalse(res.refused)
        self.assertTrue(len(res.citations) > 0)
        # Kiểm tra văn bản câu trả lời có chứa trích dẫn pháp lý chuẩn
        self.assertTrue(any("Bộ luật Lao động" in c.document_title for c in res.citations))
        self.assertTrue(any(c.formatted_citation in res.answer for c in res.citations))

    def test_03_multi_source_question(self):
        """Kiểm thử câu hỏi đòi hỏi thông tin từ nhiều nguồn."""
        q = "Quy định về thời giờ làm việc bình thường và làm thêm giờ trong lĩnh vực thăm dò dầu khí?"
        res = self.pipeline.answer(q)

        self.assertFalse(res.refused)
        self.assertTrue(len(res.citations) >= 2)
        # Các trích dẫn phải có formatted_citation hợp lệ
        for cit in res.citations:
            self.assertTrue(cit.is_valid)
            self.assertTrue(cit.formatted_citation.startswith("["))
            self.assertTrue(cit.formatted_citation.endswith("]"))

    def test_04_irrelevant_question(self):
        """Kiểm thử câu hỏi hoàn toàn ngoài phạm vi pháp luật lao động (kích hoạt từ chối chuẩn)."""
        q = "Cách mua vé xem giải bóng đá Ngoại hạng Anh mùa giải 2026?"
        res = self.pipeline.answer(q)

        self.assertTrue(res.refused)
        self.assertEqual(res.answer, STANDARD_REFUSAL_ANSWER)
        self.assertEqual(res.citations, [])
        self.assertIsNotNone(res.refusal_reason)

    def test_05_insufficient_evidence_refusal(self):
        """Kiểm thử cơ chế Pre-generation Guard từ chối sớm khi điểm tương đồng quá thấp."""
        strict_config = PipelineConfig(
            TOP_K=5,
            SIMILARITY_THRESHOLD=0.99,  # Ngưỡng cực cao để chắc chắn bị chặn sớm
            LLM_PROVIDER="mock"
        )
        strict_pipeline = TraditionalRAGPipeline(config=strict_config)

        q = "Người lao động có quyền gì?"
        res = strict_pipeline.answer(q)

        self.assertTrue(res.refused)
        self.assertEqual(res.answer, STANDARD_REFUSAL_ANSWER)
        self.assertEqual(res.generation_latency, 0.0)  # Tuyệt đối không gọi LLM generator
        self.assertTrue(res.metadata.get("pre_guard_triggered", False))

    def test_06_citation_validation(self):
        """Kiểm tra tính truy vết (traceability) của trích dẫn pháp lý tới chunks thu hồi."""
        q = "Thời gian nghỉ thai sản của lao động nữ khi sinh con?"
        res = self.pipeline.answer(q)

        self.assertFalse(res.refused)
        retrieved_chunk_ids = {c.chunk_id for c in res.retrieved_chunks}

        for cit in res.citations:
            # chunk_id trong trích dẫn phải nằm trong danh sách retrieved_chunks
            self.assertIn(cit.chunk_id, retrieved_chunk_ids)
            self.assertTrue(cit.document_title)
            # URL phải tồn tại nếu metadata gốc có
            if cit.source_url:
                self.assertTrue(cit.source_url.startswith("http"))

    def test_07_end_to_end_failure_handling(self):
        """Kiểm thử xử lý lỗi đầu vào rỗng (Fail-fast với ValueError)."""
        with self.assertRaises(ValueError):
            self.pipeline.answer("")

        with self.assertRaises(ValueError):
            self.pipeline.answer("   \n\t  ")

    def test_08_no_hidden_intelligence_verification(self):
        """Kiểm tra nguyên tắc No Hidden Intelligence: Đúng 1 retrieval, 1 context build, 1 generation."""
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = self.pipeline.retriever.retrieve("Thử việc", top_k=3)

        mock_context_builder = MagicMock()
        mock_context_builder.build_context.return_value = self.pipeline.context_builder.build_context(
            mock_retriever.retrieve.return_value
        )

        mock_generator = MagicMock()
        mock_generator.generate.return_value = self.pipeline.generator.generate(
            question="Thử việc",
            context="[SOURCE 1]\nDocument: BLLD\nContent: Thử việc 60 ngày."
        )

        test_pipeline = TraditionalRAGPipeline(
            config=self.config,
            retriever=mock_retriever,
            context_builder=mock_context_builder,
            generator=mock_generator
        )

        res = test_pipeline.answer("Thời gian thử việc là bao nhiêu ngày?")

        # Xác thực số lần gọi: Đúng 1 lần duy nhất cho mỗi mắt xích
        self.assertEqual(mock_retriever.retrieve.call_count, 1)
        self.assertEqual(mock_context_builder.build_context.call_count, 1)
        self.assertEqual(mock_generator.generate.call_count, 1)

    def test_09_latency_metrics_measurable(self):
        """Đảm bảo mọi thông số độ trễ đều được ghi nhận đầy đủ và là số thực dương."""
        q = "Mức đóng bảo hiểm thất nghiệp của người sử dụng lao động theo Luật Việc làm?"
        res = self.pipeline.answer(q)

        self.assertGreater(res.latency, 0.0)
        self.assertGreater(res.retrieval_latency, 0.0)
        self.assertGreaterEqual(res.context_latency, 0.0)
        self.assertGreaterEqual(res.generation_latency, 0.0)
        self.assertGreaterEqual(res.citation_latency, 0.0)

        # Tổng thời gian phải lớn hơn hoặc bằng thời gian thu hồi
        self.assertGreaterEqual(res.latency, res.retrieval_latency)


if __name__ == "__main__":
    unittest.main()
