"""
test_web_search_fallback.py - Unit test suite cho module Query Transformation & Web Search Fallback (RAG-13).
"""

import unittest
from CRAG.transformation.query_rewriter import LegalQueryRewriter
from CRAG.search.mock_searcher import MockLegalWebSearcher
from CRAG.search.web_searcher import LegalWebSearcher


class TestWebSearchFallback(unittest.TestCase):
    def setUp(self):
        self.rewriter = LegalQueryRewriter()
        self.mock_searcher = MockLegalWebSearcher()
        self.web_searcher = LegalWebSearcher(provider="mock")

    def test_query_rewriter_conversational_removal(self):
        """Kiểm tra loại bỏ tiền tố/hậu tố giao tiếp đời thường khỏi câu hỏi."""
        raw_query = "Cho em hỏi sếp bắt thử việc 1 năm như vậy có đúng không?"
        transformed = self.rewriter.rewrite(raw_query)

        self.assertNotIn("cho em hỏi", transformed.search_query.lower())
        self.assertNotIn("như vậy có đúng không", transformed.search_query.lower())
        self.assertIn("thử việc", transformed.search_query.lower())
        self.assertIn("lao động", transformed.search_query.lower())

    def test_query_rewriter_entity_preservation(self):
        """Kiểm tra bóc tách và bảo toàn số điều luật và số hiệu nghị định."""
        raw_query = "Xử phạt vi phạm theo Nghị định 12/2022/NĐ-CP và Điều 125 Bộ luật Lao động?"
        transformed = self.rewriter.rewrite(raw_query)

        self.assertIn("Điều 125", transformed.identified_articles)
        self.assertTrue(any("12/2022" in d for d in transformed.identified_documents))
        self.assertIn("Điều 125", transformed.search_query)

    def test_query_rewriter_domain_anchoring(self):
        """Kiểm tra bổ sung neo ngữ cảnh pháp luật lao động khi câu hỏi chưa có định danh văn bản."""
        raw_query = "Thời gian làm thêm giờ tối đa trong một tháng"
        transformed = self.rewriter.rewrite(raw_query)

        self.assertTrue(
            "lao động" in transformed.search_query.lower()
            or "pháp luật" in transformed.search_query.lower()
        )

    def test_mock_searcher_exact_keyword_hit(self):
        """Kiểm tra tìm kiếm đúng nội dung xử phạt vi phạm thử việc (Nghị định 12/2022)."""
        query = "mức phạt khi thử việc quá thời hạn quy định"
        response = self.mock_searcher.search(query=query, top_k=2)

        self.assertGreater(len(response.results), 0)
        top_res = response.results[0]
        self.assertIn("12/2022", top_res.title)
        self.assertIn("2.000.000", top_res.snippet)
        self.assertEqual(top_res.source_name, "Thư Viện Pháp Luật")

    def test_mock_searcher_latency_measurable(self):
        """Đảm bảo thông số độ trễ tìm kiếm (latency) được ghi nhận và là số thực dương."""
        response = self.mock_searcher.search(query="sa thải kỷ luật")
        self.assertGreater(response.latency, 0.0)
        self.assertEqual(response.provider, "mock_legal_search")

    def test_legal_web_searcher_dispatch(self):
        """Kiểm tra dispatcher LegalWebSearcher hoạt động trơn tru."""
        response = self.web_searcher.search(query="chế độ thai sản 6 tháng")
        self.assertGreater(len(response.results), 0)
        self.assertTrue(any("thai sản" in r.title.lower() for r in response.results))


if __name__ == "__main__":
    unittest.main()
