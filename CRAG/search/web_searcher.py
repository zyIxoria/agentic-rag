"""
CRAG Web Searcher Dispatcher.
Điều phối tìm kiếm ngoại bộ linh hoạt giữa Mock Searcher và Live Web Engine.
"""

from typing import Optional
from CRAG.config import crag_config
from CRAG.search.base import BaseWebSearcher
from CRAG.search.mock_searcher import MockLegalWebSearcher
from CRAG.search.schema import SearchResponse


class LegalWebSearcher(BaseWebSearcher):
    """
    Dispatcher chính của hệ thống Web Search Fallback trong CRAG.
    Mặc định sử dụng MockLegalWebSearcher để đảm bảo tính tái lập 100% trong môi trường nghiên cứu,
    không phụ thuộc vào mạng ngoài hay thay đổi API của bên thứ ba.
    """

    def __init__(self, provider: Optional[str] = None):
        self.provider_type = provider or crag_config.SEARCH_PROVIDER
        if self.provider_type in ["mock", "auto"]:
            self.backend: BaseWebSearcher = MockLegalWebSearcher()
        else:
            # Fallback an toàn về Mock nếu provider không xác định
            self.backend = MockLegalWebSearcher()

    def search(
        self, query: str, transformed_query: str = "", top_k: int = 3
    ) -> SearchResponse:
        return self.backend.search(
            query=query, transformed_query=transformed_query, top_k=top_k
        )
