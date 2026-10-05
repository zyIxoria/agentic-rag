"""
test_crag_pipeline.py - Unit test suite cho End-to-End CRAG Pipeline (RAG-14).
"""

import unittest
from unittest.mock import MagicMock

from RAG.pipeline.config import PipelineConfig
from RAG.retriever.schema import RetrievedChunk
from RAG.generator.base import BaseLegalGenerator, GenerationResult
from CRAG.config import CRAGConfig
from CRAG.evaluator.semantic_grader import SemanticDocumentGrader
from CRAG.pipeline.crag_pipeline import CRAGPipeline
from CRAG.pipeline.schema import CRAGResponse


class MockLegalGenerator(BaseLegalGenerator):
    """Generator giả lập phục vụ unit test tức thì và tất định."""

    def __init__(self, response_text: str = "Theo quy định tại [SOURCE 1], thời gian thử việc tối đa là 180 ngày."):
        self.model_name = "mock-model"
        self.provider = "mock"
        self.response_text = response_text

    def generate_structured(self, request) -> GenerationResult:
        context = request.context
        question = request.question
        if not context or "không tìm thấy" in question:
            return GenerationResult(
                answer="Không có đủ căn cứ pháp lý trong tài liệu.",
                citations=[],
                model_name=self.model_name,
                provider=self.provider,
                refused=True,
                reason="INSUFFICIENT_CONTEXT",
            )
        return GenerationResult(
            answer=self.response_text,
            citations=["[SOURCE 1]"],
            model_name=self.model_name,
            provider=self.provider,
            refused=False,
        )


class TestCRAGPipeline(unittest.TestCase):
    def setUp(self):
        self.mock_retriever = MagicMock()
        self.mock_generator = MockLegalGenerator()

        self.sample_chunk_125 = RetrievedChunk(
            chunk_id="BLLD_2019_Điều125_c1",
            content=(
                "Điều 125. Áp dụng hình thức xử lý kỷ luật sa thải\n"
                "1. Người lao động có hành vi trộm cắp, tham ô...\n"
                "4. Người lao động tự ý bỏ việc 05 ngày cộng dồn trong thời hạn 30 ngày."
            ),
            score=0.88,
            distance=0.12,
            rank=1,
            metadata={
                "document_id": "BLLD_2019",
                "document_title": "Bộ luật Lao động 2019",
                "document_number": "45/2019/QH14",
                "article_number": "Điều 125",
                "article_title": "Áp dụng hình thức xử lý kỷ luật sa thải",
            },
        )

        self.sample_chunk_irrelevant = RetrievedChunk(
            chunk_id="QC_2020_c1",
            content="Quy chuẩn kỹ thuật quốc gia về điều kiện chiếu sáng văn phòng làm việc.",
            score=0.30,
            distance=0.70,
            rank=1,
            metadata={
                "document_id": "QCVN_2020",
                "document_title": "Quy chuẩn kỹ thuật",
                "article_number": "Điều 1",
            },
        )

        self.crag_cfg = CRAGConfig(
            UPPER_THRESHOLD=0.68,
            LOWER_THRESHOLD=0.45,
            STRIP_THRESHOLD=0.50,
            SEARCH_PROVIDER="mock",
        )

        self.pipeline = CRAGPipeline(
            crag_cfg=self.crag_cfg,
            retriever=self.mock_retriever,
            generator=self.mock_generator,
        )

    def test_crag_pipeline_action_refine(self):
        """Kiểm tra luồng REFINE: Chunks tin cậy -> Tinh lọc nội bộ -> Sinh câu trả lời."""
        self.mock_retriever.retrieve.return_value = [self.sample_chunk_125]

        query = "Trường hợp nào người lao động bị sa thải kỷ luật theo Điều 125?"
        response: CRAGResponse = self.pipeline.answer(query)

        self.assertEqual(response.action_taken, "REFINE")
        self.assertFalse(response.refused)
        self.assertIsNotNone(response.refined_context)
        self.assertGreaterEqual(response.refined_context.compression_ratio, 0.0)
        self.assertIn("Điều 125", response.answer)
        self.assertGreater(len(response.citations), 0)
        self.assertGreater(response.telemetry.refinement_latency, 0.0)

    def test_crag_pipeline_action_refuse_out_of_scope(self):
        """Kiểm tra luồng REFUSE: Câu hỏi ngoài phạm vi bị từ chối ngay lập tức không gọi LLM."""
        self.mock_retriever.retrieve.return_value = [self.sample_chunk_irrelevant]

        query = "Thủ tục xin cấp hộ chiếu phổ thông và visa đi nước ngoài"
        response: CRAGResponse = self.pipeline.answer(query)

        self.assertEqual(response.action_taken, "REFUSE")
        self.assertTrue(response.refused)
        self.assertIn("Hệ thống xác định", response.refusal_reason)
        # Latency generation phải bằng 0 do không gọi LLM
        self.assertEqual(response.telemetry.generation_latency, 0.0)

    def test_crag_pipeline_action_web_search(self):
        """Kiểm tra luồng WEB_SEARCH: Chunks nội bộ không liên quan -> Kích hoạt tìm kiếm ngoài."""
        self.mock_retriever.retrieve.return_value = [self.sample_chunk_irrelevant]

        # Câu hỏi trong phạm vi lao động nhưng nội bộ không có chunk nào đúng
        query = "Mức phạt tiền khi người sử dụng lao động bắt thử việc quá thời hạn theo Nghị định 12/2022"
        response: CRAGResponse = self.pipeline.answer(query)

        self.assertEqual(response.action_taken, "WEB_SEARCH")
        self.assertIsNotNone(response.search_response)
        self.assertGreater(len(response.search_response.results), 0)
        self.assertGreater(response.telemetry.search_latency, 0.0)

    def test_crag_pipeline_telemetry(self):
        """Đảm bảo mọi số liệu độ trễ telemetry đều được ghi nhận đầy đủ."""
        self.mock_retriever.retrieve.return_value = [self.sample_chunk_125]

        query = "Quy định sa thải Điều 125"
        response: CRAGResponse = self.pipeline.answer(query)

        self.assertGreaterEqual(response.telemetry.retrieval_latency, 0.0)
        self.assertGreaterEqual(response.telemetry.grading_latency, 0.0)
        self.assertGreaterEqual(response.telemetry.total_latency, 0.0)

    def test_crag_pipeline_empty_query_fail_fast(self):
        """Kiểm tra xử lý câu hỏi rỗng ném lỗi ValueError."""
        with self.assertRaises(ValueError):
            self.pipeline.answer("")


if __name__ == "__main__":
    unittest.main()
