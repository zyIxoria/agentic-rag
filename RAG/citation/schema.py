"""schema.py - Cấu trúc dữ liệu cho phân hệ Citation Mapping (TASK RAG-06)."""

from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class LegalCitation(BaseModel):
    """Mô hình dữ liệu đại diện cho một trích dẫn pháp lý được ánh xạ đầy đủ từ metadata."""

    model_config = ConfigDict(extra="ignore")

    source_id: str = Field(..., description="Nhãn định danh nguồn (VD: '[SOURCE 1]')")
    source_number: Optional[int] = Field(default=None, description="Số thứ tự nguồn (1, 2, ...)")
    chunk_id: Optional[str] = Field(default=None, description="Mã định danh chunk gốc")
    document_title: str = Field(..., description="Tên văn bản quy phạm pháp luật")
    document_number: Optional[str] = Field(default=None, description="Số hiệu văn bản pháp lý")
    article_number: Optional[str] = Field(default=None, description="Số hiệu Điều")
    article_title: Optional[str] = Field(default=None, description="Tiêu đề Điều luật")
    clause_number: Optional[str] = Field(default=None, description="Số thứ tự Khoản")
    point_number: Optional[str] = Field(default=None, description="Ký hiệu Điểm")
    source_url: Optional[str] = Field(default=None, description="Đường dẫn tra cứu chính thức")
    formatted_citation: str = Field(..., description="Chuỗi trích dẫn pháp lý chuẩn (VD: '[Bộ luật Lao động 2019, Điều 125]')")
    is_valid: bool = Field(default=True, description="True nếu trích dẫn được ánh xạ thành công từ metadata thật")
    validation_error: Optional[str] = Field(default=None, description="Chi tiết lỗi nếu trích dẫn không hợp lệ")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_number": self.source_number,
            "chunk_id": self.chunk_id,
            "document_title": self.document_title,
            "document_number": self.document_number,
            "article_number": self.article_number,
            "article_title": self.article_title,
            "clause_number": self.clause_number,
            "point_number": self.point_number,
            "source_url": self.source_url,
            "formatted_citation": self.formatted_citation,
            "is_valid": self.is_valid,
            "validation_error": self.validation_error,
        }


class CitationResolutionResult(BaseModel):
    """Kết quả phân giải trích dẫn toàn diện cho câu trả lời."""

    model_config = ConfigDict(extra="ignore")

    original_answer: str = Field(..., description="Văn bản câu trả lời ban đầu từ Generator")
    enriched_answer: str = Field(..., description="Văn bản câu trả lời sau khi ánh xạ trích dẫn và phụ lục")
    valid_citations: List[LegalCitation] = Field(default_factory=list, description="Danh sách các trích dẫn hợp lệ")
    invalid_citations: List[str] = Field(default_factory=list, description="Danh sách các thẻ trích dẫn không hợp lệ bị từ chối")
    has_invalid_citations: bool = Field(default=False, description="True nếu phát hiện có trích dẫn không hợp lệ")
    citations_count: int = Field(default=0, description="Tổng số trích dẫn hợp lệ được ánh xạ")
    footnotes: List[str] = Field(default_factory=list, description="Danh mục tài liệu tham chiếu đính kèm")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_answer": self.original_answer,
            "enriched_answer": self.enriched_answer,
            "valid_citations": [c.to_dict() for c in self.valid_citations],
            "invalid_citations": self.invalid_citations,
            "has_invalid_citations": self.has_invalid_citations,
            "citations_count": self.citations_count,
            "footnotes": self.footnotes,
        }
