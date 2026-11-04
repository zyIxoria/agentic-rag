"""
Unit tests for Live Legal Web Searcher and Fallback Chain.
"""

import unittest
from unittest.mock import patch, MagicMock
from CRAG.search.live_searcher import LiveLegalWebSearcher
from CRAG.search.web_searcher import LegalWebSearcher
from CRAG.search.schema import SearchResponse, WebSearchResult


class TestLiveWebSearcher(unittest.TestCase):
    def setUp(self):
        self.searcher = LiveLegalWebSearcher(timeout_sec=5.0)

    def test_domain_identification(self):
        """Kiểm tra nhận diện tên miền pháp lý uy tín."""
        self.assertEqual(
            self.searcher._get_source_name("https://thuvienphapluat.vn/van-ban/lao-dong/123.aspx"),
            "Thư Viện Pháp Luật",
        )
        self.assertEqual(
            self.searcher._get_source_name("https://luatvietnam.vn/lao-dong/abc.html"),
            "Luật Việt Nam",
        )
        self.assertEqual(
            self.searcher._get_source_name("https://chinhphu.vn/portal/page/portal/chinhphu/hethongvanban"),
            "Cổng TTĐT Chính Phủ",
        )
        self.assertEqual(
            self.searcher._get_source_name("https://example.com/test"),
            "example.com",
        )

    def test_live_search_execution(self):
        """Kiểm tra gọi live search thực tế qua DDGS."""
        resp = self.searcher.search("Bo luat lao dong 2019", top_k=2)
        self.assertIsInstance(resp, SearchResponse)
        self.assertEqual(resp.provider, "duckduckgo")
        # Nếu có internet, sẽ có kết quả; nếu offline, resp.results là list rỗng nhưng không crash
        self.assertIsInstance(resp.results, list)
        if resp.results:
            first = resp.results[0]
            self.assertTrue(len(first.title) > 0)
            self.assertTrue(first.url.startswith("http"))

    def test_fallback_chain_mock_mode(self):
        """Kiểm tra khi cấu hình rõ provider='mock'."""
        dispatcher = LegalWebSearcher(provider="mock")
        resp = dispatcher.search("sa thải kỷ luật", top_k=2)
        self.assertTrue("mock" in resp.provider)
        self.assertGreater(len(resp.results), 0)

    @patch.object(LiveLegalWebSearcher, "search")
    def test_fallback_chain_on_live_failure(self, mock_live_search):
        """Kiểm tra fallback sang mock khi live search gặp sự cố (offline, timeout, lỗi mạng)."""
        mock_live_search.side_effect = RuntimeError("Network connection timed out")
        
        dispatcher = LegalWebSearcher(provider="auto")
        resp = dispatcher.search("thử việc quá hạn", top_k=2)
        
        # Phải fallback an toàn về mock
        self.assertTrue("mock" in resp.provider)
        self.assertGreater(len(resp.results), 0)
        self.assertTrue(any("Nghị định 12/2022" in r.title for r in resp.results))

    @patch.object(LiveLegalWebSearcher, "search")
    def test_fallback_chain_on_empty_live_results(self, mock_live_search):
        """Kiểm tra fallback sang mock khi live search trả về 0 kết quả."""
        mock_live_search.return_value = SearchResponse(
            query="test",
            transformed_query="",
            results=[],
            latency=0.1,
            provider="duckduckgo",
            total_found=0,
        )
        
        dispatcher = LegalWebSearcher(provider="auto")
        resp = dispatcher.search("nghỉ thai sản bảo hiểm", top_k=2)
        
        self.assertTrue("mock" in resp.provider)
        self.assertGreater(len(resp.results), 0)


if __name__ == "__main__":
    unittest.main()
