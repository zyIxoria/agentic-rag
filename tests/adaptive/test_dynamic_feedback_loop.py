"""
Unit tests for Dynamic 2-Way Feedback Loop and Post-Retrieval Escalation.
"""

import unittest
from unittest.mock import MagicMock, patch
from Adaptive_RAG.orchestration.feedback_evaluator import (
    PostRetrievalConfidenceEvaluator,
    ConfidenceLevel,
    EscalationTarget,
    PostRetrievalEvaluation,
)
from Adaptive_RAG.orchestration.orchestrator import AdaptiveOrchestrator
from Adaptive_RAG.classifier.schema import (
    ClassificationResult,
    ComplexityLevel,
    QueryIntent,
    RoutingDecision,
)
from RAG.retriever.schema import RetrievedChunk
from CRAG.search.schema import SearchResponse, WebSearchResult


class TestDynamicFeedbackLoop(unittest.TestCase):
    def setUp(self):
        self.evaluator = PostRetrievalConfidenceEvaluator()

    def test_post_retrieval_empty_chunks(self):
        """Kiểm tra khi tập chunks sau truy xuất bị rỗng."""
        eval_res = self.evaluator.evaluate("thời hạn thử việc", [])
        self.assertEqual(eval_res.confidence_level, ConfidenceLevel.EMPTY)
        self.assertEqual(eval_res.recommended_action, EscalationTarget.ESCALATE_TO_CRAG)
        self.assertEqual(eval_res.num_chunks, 0)

    def test_post_retrieval_high_confidence(self):
        """Kiểm tra khi tập chunks có điều luật khớp hoàn toàn chủ đề."""
        chunk = RetrievedChunk(
            chunk_id="BLLD_2019_D25",
            content="Điều 25. Thời gian thử việc do hai bên thỏa thuận căn cứ vào tính chất và mức độ phức tạp...",
            score=0.92,
            rank=1,
            metadata={
                "document_name": "Bộ luật Lao động 2019",
                "article": "Điều 25",
                "title": "Thời gian thử việc",
            },
        )
        eval_res = self.evaluator.evaluate("thời gian thử việc tối đa", [chunk])
        self.assertEqual(eval_res.confidence_level, ConfidenceLevel.HIGH)
        self.assertEqual(eval_res.recommended_action, EscalationTarget.NONE)
        self.assertGreaterEqual(eval_res.num_relevant, 1)

    def test_post_retrieval_low_confidence_irrelevant_chunks(self):
        """Kiểm tra khi chunks thu hồi bị lạc đề (out of scope)."""
        chunk = RetrievedChunk(
            chunk_id="IRRELEVANT_01",
            content="Quy định về đào tạo phi công, cấp giấy phép lái máy bay thương mại và an toàn hàng không...",
            score=0.40,
            rank=1,
            metadata={
                "document_name": "Luật Hàng không Dân dụng",
                "article": "Điều 10",
                "title": "Tiêu chuẩn nhân viên hàng không",
            },
        )
        eval_res = self.evaluator.evaluate("thời gian thử việc", [chunk])
        self.assertEqual(eval_res.confidence_level, ConfidenceLevel.LOW)
        self.assertEqual(eval_res.recommended_action, EscalationTarget.ESCALATE_TO_CRAG)

    def test_subquery_evaluation_web_search_trigger(self):
        """Kiểm tra subquery bị rỗng tự động kích hoạt Web Search Fallback."""
        sub_eval = self.evaluator.evaluate_subquery("mức xử phạt vi phạm thử việc theo nghị định 12/2022", [])
        self.assertEqual(sub_eval.confidence_level, ConfidenceLevel.EMPTY)
        self.assertEqual(sub_eval.recommended_action, EscalationTarget.WEB_SEARCH_SUBQUERY)

    def test_orchestrator_dynamic_escalation_from_traditional_to_crag(self):
        """Kiểm tra Orchestrator tự động ESCALATE từ TRADITIONAL_RAG sang CRAG khi retrieval có confidence LOW."""
        mock_classifier = MagicMock()
        mock_classifier.classify.return_value = ClassificationResult(
            query="xử phạt hành chính khi thử việc quá hạn",
            intent=QueryIntent.LEGAL_DIRECT_DEFINITION,
            complexity=ComplexityLevel.SIMPLE_SINGLE_HOP,
            suggested_route=RoutingDecision.TRADITIONAL_RAG,
            confidence=0.95,
        )

        mock_retriever = MagicMock()
        # Trả về chunk lạc đề khiến post_evaluator chấm INCORRECT/LOW
        mock_retriever.retrieve.return_value = [
            RetrievedChunk(
                chunk_id="NO_MATCH",
                content="Về tiêu chuẩn an toàn hàng không và bay quốc tế",
                score=0.35,
                rank=1,
                metadata={"title": "Hàng không", "article": "Điều 1"},
            )
        ]

        mock_crag_pipeline = MagicMock()
        mock_crag_resp = MagicMock()
        mock_crag_resp.answer = "Theo Nghị định 12/2022/NĐ-CP, phạt tiền từ 2 đến 5 triệu đồng."
        mock_crag_resp.citations = ["Nghị định 12/2022/NĐ-CP"]
        mock_crag_resp.retrieved_chunks = []
        mock_crag_resp.refused = False
        mock_crag_resp.refusal_reason = None
        mock_crag_pipeline.answer.return_value = mock_crag_resp

        orchestrator = AdaptiveOrchestrator(
            classifier=mock_classifier,
            retriever=mock_retriever,
            crag_pipeline=mock_crag_pipeline,
        )

        resp = orchestrator.route_and_execute("xử phạt hành chính khi thử việc quá hạn")

        # Kiểm tra phản hồi 2 chiều đã tự động escalate sang CRAG
        self.assertTrue(resp.escalated)
        self.assertEqual(resp.route_taken, RoutingDecision.CORRECTIVE_RAG)
        self.assertEqual(resp.trace.original_route, RoutingDecision.TRADITIONAL_RAG)
        self.assertIn("Nghị định 12/2022", resp.answer)


if __name__ == "__main__":
    unittest.main()
