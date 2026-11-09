"""
Adaptive RAG Base Classifier Interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from Adaptive_RAG.config import AdaptiveRAGConfig, adaptive_config
from Adaptive_RAG.classifier.schema import ClassificationResult


class BaseQueryClassifier(ABC):
    """Giao diện trừu tượng cho bộ phân loại độ phức tạp câu hỏi."""

    def __init__(self, config: Optional[AdaptiveRAGConfig] = None):
        self.config = config or adaptive_config

    @abstractmethod
    def classify(
        self,
        query: str,
        chat_history: Optional[Any] = None
    ) -> ClassificationResult:
        """
        Phân loại câu hỏi người dùng thành các mức độ phức tạp và hướng điều phối phù hợp.
        Hỗ trợ nhận diện ngữ cảnh hội thoại đa lượt qua chat_history.
        """
        pass
