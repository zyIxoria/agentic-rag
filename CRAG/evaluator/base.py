"""base.py - Lớp cơ sở trừu tượng cho Retrieval Evaluator (Document Grader)."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional

from CRAG.evaluator.schema import DocumentGrade, RetrievalGradingResult
from RAG.retriever.schema import RetrievedChunk
from CRAG.config import CRAGConfig, default_crag_config


class BaseDocumentGrader(ABC):
    """Giao diện chung cho các bộ đánh giá tài liệu thu hồi trong Corrective RAG."""

    def __init__(self, config: Optional[CRAGConfig] = None):
        self.config = config or default_crag_config

    @abstractmethod
    def grade_document(self, query: str, chunk: RetrievedChunk) -> DocumentGrade:
        """Chấm điểm mức độ liên quan của một đoạn tài liệu đối với câu hỏi."""
        pass

    @abstractmethod
    def grade_documents(self, query: str, chunks: List[RetrievedChunk]) -> RetrievalGradingResult:
        """Đánh giá toàn bộ danh sách Top-K chunks và đưa ra quyết định hành động tổng thể."""
        pass
