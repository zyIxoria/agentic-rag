"""schema.py - Cấu trúc dữ liệu cho phân hệ Legal Context Builder (TASK RAG-04).

Định nghĩa các mô hình dữ liệu phục vụ đóng gói ngữ cảnh cho LLM:
- ContextSource: Thông tin của một nguồn trích dẫn đã được định dạng ([SOURCE 1], [SOURCE 2], ...).
- BuildContextResult: Kết quả đóng gói toàn diện bao gồm chuỗi ngữ cảnh, danh sách nguồn,
  các nguồn bị cắt giảm do tràn ngân sách token, và bản đồ trích dẫn (citation mapping).
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

from RAG.retriever.schema import RetrievedChunk


class ContextSource(BaseModel):
    """Đại diện cho một nguồn tài liệu pháp lý được định dạng trong context."""

    source_id: str = Field(..., description="Nhãn định danh ổn định của nguồn (VD: '[SOURCE 1]')")
    source_number: int = Field(..., ge=1, description="Số thứ tự của nguồn (1, 2, ...)")
    chunk_id: str = Field(..., description="Mã định danh chunk gốc từ Dataset V2.1")
    score: float = Field(..., description="Điểm tương đồng Cosine Similarity thu hồi từ RAG-03")
    rank: int = Field(..., ge=1, description="Thứ hạng ban đầu từ retriever")
    document_title: str = Field(..., description="Tên văn bản quy phạm pháp luật")
    document_number: Optional[str] = Field(default=None, description="Số hiệu văn bản pháp lý")
    article_number: Optional[str] = Field(default=None, description="Số hiệu Điều")
    article_title: Optional[str] = Field(default=None, description="Tiêu đề Điều luật")
    clause_number: Optional[str] = Field(default=None, description="Số thứ tự Khoản")
    point_number: Optional[str] = Field(default=None, description="Ký hiệu Điểm")
    content: str = Field(..., description="Toàn văn nội dung đoạn trích nguyên bản")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Siêu dữ liệu pháp lý đầy đủ")
    token_count: int = Field(default=0, ge=0, description="Số token ước tính của khối nguồn này")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_number": self.source_number,
            "chunk_id": self.chunk_id,
            "score": self.score,
            "rank": self.rank,
            "document_title": self.document_title,
            "document_number": self.document_number,
            "article_number": self.article_number,
            "article_title": self.article_title,
            "clause_number": self.clause_number,
            "point_number": self.point_number,
            "token_count": self.token_count,
            "metadata": self.metadata,
        }


class BuildContextResult(BaseModel):
    """Kết quả hoàn chỉnh của quá trình đóng gói ngữ cảnh cho LLM."""

    context_text: str = Field(..., description="Toàn bộ chuỗi văn bản ngữ cảnh có cấu trúc")
    sources: List[ContextSource] = Field(default_factory=list, description="Danh sách các nguồn được đưa vào context")
    dropped_sources: List[RetrievedChunk] = Field(default_factory=list, description="Các chunk bị cắt bỏ do vượt ngưỡng MAX_CONTEXT_TOKENS")
    total_tokens: int = Field(default=0, ge=0, description="Tổng số token ước tính của context_text")
    max_context_tokens: int = Field(..., description="Ngưỡng trần token cấu hình")
    num_retrieved: int = Field(default=0, description="Tổng số chunks nhận vào từ retriever")
    num_included: int = Field(default=0, description="Số lượng nguồn được đưa vào context")
    num_dropped: int = Field(default=0, description="Số lượng nguồn bị cắt giảm")
    citation_mapping: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Bản đồ tra cứu từ '[SOURCE X]' sang siêu dữ liệu pháp lý"
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_text": self.context_text,
            "total_tokens": self.total_tokens,
            "max_context_tokens": self.max_context_tokens,
            "num_retrieved": self.num_retrieved,
            "num_included": self.num_included,
            "num_dropped": self.num_dropped,
            "sources": [s.to_dict() for s in self.sources],
            "dropped_sources": [c.to_dict() for c in self.dropped_sources],
            "citation_mapping": self.citation_mapping,
        }
