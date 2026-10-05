"""
test_adaptive_orchestrator.py - Unit test suite cho Adaptive Orchestrator & Multi-Hop Dispatcher (RAG-17).
"""

import unittest
from unittest.mock import MagicMock

from RAG.retriever.schema import RetrievedChunk
from RAG.generator.base import BaseLegalGenerator, GenerationResult
from Adaptive_RAG.classifier.schema import RoutingDecision
from Adaptive_RAG.orchestration.orchestrator import AdaptiveOrchestrator
from Adaptive_RAG.orchestration.schema import AdaptiveRAGResponse


class MockOrchestratorGenerator(BaseLegalGenerator):
    """Generator giả lập phục vụ unit test cho Orchestrator."""

    def __init__(self):
        super().__init__()
        self.model_name = "mock-orch-model"
        self.provider = "mock"

    def generate_structured(self, request) -> GenerationResult:
        context = request.context
        return GenerationResult(
            answer="Dựa trên các quy định được viện dẫn tại [SOURCE 1], yêu cầu pháp lý đã được thỏa mãn.",
            citations=["[SOURCE 1]"],
            model_name=self.model_name,
            provider=self.provider,
            refused=False,
        )


class TestAdaptiveOrchestrator(unittest.TestCase):
    def setUp(self):
        self.mock_retriever = MagicMock()
        self.mock_generator = MockOrchestratorGenerator()

        self.sample_chunk_1 = RetrievedChunk(
            chunk_id="BLLD_2019_Điều25_c1",
            content="Điều 25. Thời gian thử việc. Thời gian thử việc do hai bên thỏa thuận...",
            score=0.88,
            distance=0.12,
            rank=1,
            metadata={
                "document_id": "BLLD_2019",
                "document_title": "Bộ luật Lao động 2019",
                "article_number": "Điều 25",
            },
        )
        self.sample_chunk_2 = RetrievedChunk(
            chunk_id="ND145_2020_Điều10_c1",
            content="Nghị định 145/2020/NĐ-CP. Hướng dẫn chi tiết thi hành Điều 25 về thử việc...",
            score=0.82,
            distance=0.18,
            rank=2,
            metadata={
                "document_id": "ND145_2020",
                "document_title": "Nghị định 145/2020/NĐ-CP",
                "article_number": "Điều 10",
            },
        )

        self.mock_retriever.retrieve.return_value = [
            self.sample_chunk_1,
            self.sample_chunk_2,
        ]

        self.orchestrator = AdaptiveOrchestrator(
            retriever=self.mock_retriever,
            generator=self.mock_generator,
        )

    def test_orchestrator_direct_answer(self):
        """Kiểm tra điều phối DIRECT_ANSWER phản hồi lập tức với câu hỏi chào hỏi."""
        q = "Xin chào bạn!"
        resp: AdaptiveRAGResponse = self.orchestrator.route_and_execute(q)

        self.assertEqual(resp.route_taken, RoutingDecision.DIRECT_ANSWER)
        self.assertFalse(resp.refused)
        self.assertEqual(len(resp.retrieved_chunks), 0)
        self.assertIn("trợ lý ảo", resp.answer.lower())
        self.assertLess(resp.latency_ms, 50.0)

    def test_orchestrator_direct_refusal(self):
        """Kiểm tra điều phối DIRECT_REFUSAL từ chối an toàn ngay câu hỏi ngoài phạm vi."""
        q = "Hồ sơ và thủ tục xin visa du lịch Schengen gồm những gì?"
        resp: AdaptiveRAGResponse = self.orchestrator.route_and_execute(q)

        self.assertEqual(resp.route_taken, RoutingDecision.DIRECT_REFUSAL)
        self.assertTrue(resp.refused)
        self.assertEqual(len(resp.retrieved_chunks), 0)
        self.assertIn("ngoài phạm vi", resp.answer.lower())

    def test_orchestrator_traditional_rag(self):
        """Kiểm tra điều phối TRADITIONAL_RAG cho câu hỏi tra cứu đơn giản 1 điều luật."""
        q = "Điều 125 Bộ luật Lao động quy định về gì?"
        resp: AdaptiveRAGResponse = self.orchestrator.route_and_execute(q)

        self.assertEqual(resp.route_taken, RoutingDecision.TRADITIONAL_RAG)
        self.assertGreater(len(resp.retrieved_chunks), 0)

    def test_orchestrator_corrective_rag(self):
        """Kiểm tra điều phối CORRECTIVE_RAG cho câu hỏi về quy trình, thủ tục."""
        q = "Trình tự, thủ tục các bước tiến hành xử lý kỷ luật sa thải người lao động"
        resp: AdaptiveRAGResponse = self.orchestrator.route_and_execute(q)

        self.assertEqual(resp.route_taken, RoutingDecision.CORRECTIVE_RAG)
        self.assertGreater(len(resp.retrieved_chunks), 0)

    def test_orchestrator_decompose_agentic(self):
        """Kiểm tra điều phối DECOMPOSE_AGENTIC cho câu hỏi liên văn bản đa chặng."""
        q = "So sánh quy định về thời gian thử việc giữa Bộ luật Lao động 2019 và Nghị định 145/2020"
        resp: AdaptiveRAGResponse = self.orchestrator.route_and_execute(q)

        self.assertEqual(resp.route_taken, RoutingDecision.DECOMPOSE_AGENTIC)
        self.assertIsNotNone(resp.trace.plan)
        self.assertGreaterEqual(len(resp.trace.plan.sub_queries), 2)
        self.assertGreater(len(resp.retrieved_chunks), 0)
        self.assertGreater(resp.trace.synthesis_latency_ms, 0.0)

    def test_orchestrator_empty_query_fail_fast(self):
        """Kiểm tra xử lý câu hỏi rỗng an toàn ném ValueError."""
        with self.assertRaises(ValueError):
            self.orchestrator.route_and_execute("")


if __name__ == "__main__":
    unittest.main()
