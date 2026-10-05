"""
CRAG Base Web Searcher Interface.
"""

from abc import ABC, abstractmethod
from CRAG.search.schema import SearchResponse


class BaseWebSearcher(ABC):
    """Giao diện trừu tượng cho Web Search Fallback Engine."""

    @abstractmethod
    def search(
        self, query: str, transformed_query: str = "", top_k: int = 3
    ) -> SearchResponse:
        """
        Thực hiện tìm kiếm tri thức ngoại bộ khi retrieval nội bộ bị chấm điểm INCORRECT/AMBIGUOUS.
        """
        pass
