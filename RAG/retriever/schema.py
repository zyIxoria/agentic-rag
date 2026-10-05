"""schema.py - Cấu trúc dữ liệu cho phân hệ Dense Semantic Retrieval (TASK RAG-03).

Định nghĩa mô hình dữ liệu RetrievedChunk chứa đầy đủ các trường bắt buộc:
- chunk_id: Định danh duy nhất toàn cục từ Dataset V2.1.
- content: Nội dung đoạn trích pháp luật.
- score: Điểm tương đồng ngữ nghĩa (Cosine Similarity).
- metadata: Toàn bộ 18 trường siêu dữ liệu pháp lý (bao gồm các trường None đã khôi phục).
- rank: Thứ hạng từ 1 đến K.
- distance: Khoảng cách Cosine Distance nguyên bản từ ChromaDB.
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class RetrievedChunk(BaseModel):
    """Đại diện cho một đoạn văn bản pháp lý được thu hồi từ Dense Vector Search."""

    chunk_id: str = Field(..., description="Định danh duy nhất của chunk từ Dataset V2.1")
    content: str = Field(..., description="Toàn văn nội dung đoạn pháp lý")
    score: float = Field(..., description="Điểm tương đồng Cosine Similarity (score = 1.0 - distance)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Siêu dữ liệu pháp lý đầy đủ")
    rank: int = Field(..., ge=1, description="Thứ hạng của chunk trong kết quả tìm kiếm (1-indexed)")
    distance: Optional[float] = Field(default=None, description="Khoảng cách Cosine Distance nguyên bản từ Vector Store")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True
    )

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi đối tượng sang định dạng dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "score": self.score,
            "rank": self.rank,
            "distance": self.distance,
            "metadata": self.metadata,
        }
