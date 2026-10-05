"""
test_adaptive_pipeline.py - Unit test suite cho End-to-End Adaptive RAG Pipeline (RAG-18).
"""

import unittest
from unittest.mock import MagicMock

from RAG.retriever.schema import RetrievedChunk
from RAG.generator.base import BaseLegalGenerator, GenerationResult
from Adaptive_RAG.classifier.schema import RoutingDecision
from Adaptive_RAG.pipeline.adaptive_pipeline import AdaptiveRAGPipeline
from Adaptive_RAG.orchestration.schema import AdaptiveRAGResponse


class MockPipelineGenerator(BaseLegalGenerator):
    """Generator giả lập phục vụ unit test cho AdaptiveRAGPipeline."""

    def __init__(self):
        super().__init__()
        self.model_name = "mock-adaptive-model"
        self.provider = "mock"

    def generate_structured(self, request) -> GenerationResult:
        return GenerationResult(
            answer="Căn cứ theo quy định tại [SOURCE 1], yêu cầu pháp lý được giải quyết như sau.",
            citations=["[SOURCE 1]"],
            model_name=self.model_name,
            provider=self.provider,
            refused=False,
        )


class TestAdaptiveRAGPipeline(unittest.TestCase):
    def setUp(self):
        self.mock_retriever = MagicMock()
        self.mock_generator = MockPipelineGenerator()

        self.sample_chunk = RetrievedChunk(
            chunk_id="BLLD_2019_Điều125_c1",
            content="Điều 125. Áp dụng hình thức xử lý kỷ luật sa thải...",
            score=0.85,
            distance=0.15,
            rank=1,
            metadata={
                "document_id": "BLLD_2019",
                "document_title": "Bộ luật Lao động 2019",
                "article_number": "Điều 125",
            },
        )

        self.mock_retriever.retrieve.return_value = [self.sample_chunk]

        self.pipeline = AdaptiveRAGPipeline(
            retriever=self.mock_retriever,
            generator=self.mock_generator,
        )

    def test_pipeline_e2e_direct_greeting(self):
        """Kiểm tra luồng trực tiếp phản hồi câu hỏi chào hỏi."""
        resp: AdaptiveRAGResponse = self.pipeline.answer("Chào bạn")
        self.assertEqual(resp.route_taken, RoutingDecision.DIRECT_ANSWER)
        self.assertFalse(resp.refused)
        self.assertIn("trợ lý ảo", resp.answer.lower())

    def test_pipeline_e2e_direct_refusal(self):
        """Kiểm tra luồng trực tiếp từ chối câu hỏi ngoài phạm vi."""
        resp: AdaptiveRAGResponse = self.pipeline.answer("Thủ tục đăng ký kết hôn giữa công dân Việt Nam")
        self.assertEqual(resp.route_taken, RoutingDecision.DIRECT_REFUSAL)
        self.assertTrue(resp.refused)

    def test_pipeline_e2e_traditional(self):
        """Kiểm tra luồng Traditional RAG cho câu hỏi tra cứu đơn giản."""
        resp: AdaptiveRAGResponse = self.pipeline.answer("Điều 125 Bộ luật Lao động")
        self.assertEqual(resp.route_taken, RoutingDecision.TRADITIONAL_RAG)
        self.assertGreater(len(resp.retrieved_chunks), 0)

    def test_pipeline_e2e_complex_decomposition(self):
        """Kiểm tra luồng Decompose Agentic cho câu hỏi phức tạp."""
        q = "So sánh quy định về thời gian thử việc giữa Bộ luật Lao động 2019 và Nghị định 145/2020"
        resp: AdaptiveRAGResponse = self.pipeline.answer(q)
        self.assertEqual(resp.route_taken, RoutingDecision.DECOMPOSE_AGENTIC)
        self.assertIsNotNone(resp.trace.plan)
        self.assertGreaterEqual(len(resp.trace.plan.sub_queries), 2)

    def test_pipeline_e2e_empty_query_fail_fast(self):
        """Kiểm tra xử lý câu hỏi rỗng ném ValueError."""
        with self.assertRaises(ValueError):
            self.pipeline.answer("")


if __name__ == "__main__":
    unittest.main()
