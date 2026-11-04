"""
CRAG Web Searcher Dispatcher.
Điều phối tìm kiếm ngoại bộ thông minh kết hợp Live Web Search Engine thực tế
với Fallback Chain an toàn về Mock Searcher khi ngoại tuyến hoặc bị rate-limit.
"""

import logging
from typing import Optional
from CRAG.config import crag_config
from CRAG.search.base import BaseWebSearcher
from CRAG.search.mock_searcher import MockLegalWebSearcher
from CRAG.search.live_searcher import LiveLegalWebSearcher
from CRAG.search.schema import SearchResponse

logger = logging.getLogger(__name__)


class LegalWebSearcher(BaseWebSearcher):
    """
    Dispatcher chính của hệ thống Web Search Fallback trong CRAG.
    
    Chiến lược Fallback Chain 3 lớp:
    1. Lớp 1 (Live Web): Tra cứu trực tiếp trên Internet qua LiveLegalWebSearcher (DuckDuckGo/Serper/Tavily)
       để cập nhật văn bản mới nhất từ các cổng pháp luật chính thống (thuvienphapluat.vn, moj.gov.vn, chinhphu.vn...).
    2. Lớp 2 (Mock Searcher): Nếu mất mạng, timeout hoặc nhà cung cấp chặn bot, tự động chuyển đổi an toàn sang
       MockLegalWebSearcher chứa tri thức án lệ và nghị định định sẵn.
    3. Lớp 3 (Graceful Fallback): Trả về phản hồi rỗng an toàn, không làm đổ vỡ luồng xử lý RAG.
    """

    def __init__(self, provider: Optional[str] = None):
        self.provider_type = (provider or crag_config.SEARCH_PROVIDER).lower()
        self.mock_backend = MockLegalWebSearcher()
        self.live_backend = LiveLegalWebSearcher(provider=self.provider_type)

    def search(
        self, query: str, transformed_query: str = "", top_k: int = 3
    ) -> SearchResponse:
        """
        Thực thi tìm kiếm tri thức ngoại bộ qua Fallback Chain.
        """
        # Nếu cấu hình chỉ định rõ mock (cho unit test hoặc offline tuyệt đối)
        if self.provider_type == "mock":
            return self.mock_backend.search(
                query=query, transformed_query=transformed_query, top_k=top_k
            )

        # Với chế độ "auto", "duckduckgo", "live", "serper", "tavily":
        try:
            logger.info(f"Đang gọi Live Legal Web Search cho truy vấn: '{transformed_query or query}'...")
            live_response = self.live_backend.search(
                query=query, transformed_query=transformed_query, top_k=top_k
            )
            if live_response.results and len(live_response.results) > 0:
                logger.info(f"Live Web Search thành công: tìm thấy {len(live_response.results)} kết quả.")
                return live_response
            else:
                logger.warning("Live Web Search không trả về kết quả, kích hoạt fallback sang Mock Searcher.")
        except Exception as e:
            logger.warning(f"Live Web Search gặp sự cố ({e}), kích hoạt fallback an toàn sang Mock Searcher.")

        # Fallback về Mock
        mock_resp = self.mock_backend.search(
            query=query, transformed_query=transformed_query, top_k=top_k
        )
        mock_resp.provider = f"{mock_resp.provider}_fallback"
        return mock_resp
