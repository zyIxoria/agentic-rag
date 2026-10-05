"""
test_query_classifier.py - Unit test suite cho Query Complexity & Intent Classifier (RAG-15).
"""

import unittest
from Adaptive_RAG.classifier.hybrid_classifier import HybridQueryClassifier
from Adaptive_RAG.classifier.schema import (
    ComplexityLevel,
    QueryIntent,
    RoutingDecision,
)


class TestQueryClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = HybridQueryClassifier()

    def test_classify_greeting(self):
        """Kiểm tra nhận diện câu hỏi chào hỏi/xã giao định tuyến DIRECT_ANSWER."""
        queries = ["Xin chào bạn", "Hello", "Cảm ơn bạn rất nhiều", "bạn là ai"]
        for q in queries:
            res = self.classifier.classify(q)
            self.assertEqual(res.intent, QueryIntent.GREETING_CHITCHAT)
            self.assertEqual(res.complexity, ComplexityLevel.DIRECT)
            self.assertEqual(res.suggested_route, RoutingDecision.DIRECT_ANSWER)
            self.assertGreater(res.confidence, 0.90)

    def test_classify_out_of_scope(self):
        """Kiểm tra nhận diện câu hỏi ngoài phạm vi định tuyến DIRECT_REFUSAL."""
        queries = [
            "Hồ sơ và thủ tục xin cấp visa du lịch Schengen",
            "Mức xử phạt người điều khiển xe máy vi phạm nồng độ cồn",
            "Công thức và quy trình chế biến nước dùng phở bò Hà Nội",
            "Thủ tục cấp đổi thẻ căn cước công dân gắn chip",
        ]
        for q in queries:
            res = self.classifier.classify(q)
            self.assertEqual(res.intent, QueryIntent.OUT_OF_SCOPE)
            self.assertEqual(res.complexity, ComplexityLevel.DIRECT)
            self.assertEqual(res.suggested_route, RoutingDecision.DIRECT_REFUSAL)
            self.assertIn("ngoài phạm vi", res.reasoning)

    def test_classify_single_article_direct(self):
        """Kiểm tra câu hỏi đơn giản trực tiếp định tuyến TRADITIONAL_RAG."""
        q = "Điều 125 Bộ luật Lao động quy định về gì?"
        res = self.classifier.classify(q)
        self.assertEqual(res.complexity, ComplexityLevel.SIMPLE_SINGLE_HOP)
        self.assertEqual(res.suggested_route, RoutingDecision.TRADITIONAL_RAG)
        self.assertIn("Điều 125", res.detected_articles)

    def test_classify_multi_document(self):
        """Kiểm tra câu hỏi đa văn bản định tuyến DECOMPOSE_AGENTIC."""
        q = "So sánh quy định về thời gian thử việc giữa Bộ luật Lao động 2019 và Nghị định 145/2020"
        res = self.classifier.classify(q)
        self.assertEqual(res.intent, QueryIntent.LEGAL_MULTI_DOCUMENT)
        self.assertEqual(res.complexity, ComplexityLevel.COMPLEX_MULTI_HOP)
        self.assertEqual(res.suggested_route, RoutingDecision.DECOMPOSE_AGENTIC)
        self.assertGreaterEqual(len(res.detected_documents), 1)

    def test_classify_complex_conditional(self):
        """Kiểm tra câu hỏi đa điều kiện tình huống định tuyến DECOMPOSE_AGENTIC."""
        q = "Người lao động vừa tự ý bỏ việc 5 ngày vừa đang trong thời gian nuôi con nhỏ dưới 12 tháng thì có bị sa thải không và phải xử lý thế nào?"
        res = self.classifier.classify(q)
        self.assertEqual(res.complexity, ComplexityLevel.COMPLEX_MULTI_HOP)
        self.assertEqual(res.suggested_route, RoutingDecision.DECOMPOSE_AGENTIC)

    def test_classify_procedural(self):
        """Kiểm tra câu hỏi về trình tự, thủ tục định tuyến CORRECTIVE_RAG."""
        q = "Trình tự, thủ tục các bước tiến hành xử lý kỷ luật sa thải người lao động"
        res = self.classifier.classify(q)
        self.assertEqual(res.intent, QueryIntent.LEGAL_PROCEDURAL)
        self.assertEqual(res.suggested_route, RoutingDecision.CORRECTIVE_RAG)

    def test_classifier_latency_fast(self):
        """Đảm bảo tốc độ phân loại cực nhanh (< 10 ms)."""
        res = self.classifier.classify("Thời gian làm thêm giờ tối đa trong năm")
        self.assertLess(res.latency_ms, 10.0)


if __name__ == "__main__":
    unittest.main()
