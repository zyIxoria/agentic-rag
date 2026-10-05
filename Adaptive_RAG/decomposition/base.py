"""
Adaptive RAG Base Query Decomposer Interface.
"""

from abc import ABC, abstractmethod
from typing import Optional
from Adaptive_RAG.config import AdaptiveRAGConfig, adaptive_config
from Adaptive_RAG.decomposition.schema import DecompositionPlan


class BaseQueryDecomposer(ABC):
    """Giao diện trừu tượng cho bộ phân rã câu hỏi (Query Decomposer)."""

    def __init__(self, config: Optional[AdaptiveRAGConfig] = None):
        self.config = config or adaptive_config

    @abstractmethod
    def decompose(self, query: str) -> DecompositionPlan:
        """
        Phân rã câu hỏi phức tạp thành một kế hoạch thực thi các Sub-queries có cấu trúc.
        """
        pass
