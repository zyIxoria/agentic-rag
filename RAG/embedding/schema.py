"""schema.py - Định nghĩa cấu trúc dữ liệu và quy tắc bảo tồn metadata cho phân hệ Embedding.

Tuân thủ nghiêm ngặt yêu cầu của TASK RAG-01:
- Bảo tồn đầy đủ 18 trường metadata pháp lý.
- Chuẩn hóa cấu trúc record: chunk_id, content, embedding, metadata.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

# Danh mục 18 trường siêu dữ liệu bắt buộc không được làm mất theo TASK RAG-01
MANDATORY_METADATA_FIELDS = (
    "chunk_id",
    "document_id",
    "document_number",
    "document_title",
    "document_type",
    "chapter_number",
    "chapter_title",
    "article_number",
    "article_title",
    "clause_number",
    "point_number",
    "content_type",
    "effective_from",
    "effective_to",
    "legal_status",
    "source_url",
    "parent_document",
    "parent_article",
)


def infer_content_type(chunk: Dict[str, Any]) -> str:
    """Xác định content_type nếu chưa có trong chunk thô."""
    if chunk.get("content_type"):
        return str(chunk["content_type"])
    if chunk.get("point_number"):
        return "point"
    if chunk.get("clause_number"):
        return "clause"
    if chunk.get("appendix_number") or "phụ lục" in (chunk.get("article_title") or "").lower():
        return "appendix"
    if chunk.get("article_number"):
        return "article"
    return "article"


def extract_preserved_metadata(raw_chunk: Dict[str, Any]) -> Dict[str, Any]:
    """Trích xuất và bảo tồn toàn bộ 18 trường siêu dữ liệu cùng các trường mở rộng.
    
    Args:
        raw_chunk: Bản ghi chunk thô từ Dataset V2.1.
        
    Returns:
        Dictionary metadata đã bảo đảm có đủ 18 trường bắt buộc.
    """
    metadata: Dict[str, Any] = {}

    # Copy toàn bộ thuộc tính gốc để không làm mất bất kỳ trường nào (kể cả section_number, chunk_index, v.v.)
    for k, v in raw_chunk.items():
        if k != "content":  # content được tách riêng thành trường nội dung
            metadata[k] = v

    # Đảm bảo 18 trường bắt buộc luôn hiện diện
    for field in MANDATORY_METADATA_FIELDS:
        if field not in metadata:
            if field == "content_type":
                metadata["content_type"] = infer_content_type(raw_chunk)
            elif field == "chunk_id":
                metadata["chunk_id"] = raw_chunk.get("chunk_id", "")
            else:
                metadata[field] = None

    return metadata


def validate_metadata_preservation(
    source_chunk: Dict[str, Any],
    embedded_chunk_metadata: Dict[str, Any]
) -> bool:
    """Xác nhận không có trường siêu dữ liệu nào bị thất thoát hoặc sai lệch giá trị."""
    for field in MANDATORY_METADATA_FIELDS:
        if field not in embedded_chunk_metadata:
            return False
        # Nếu trường có trong source, giá trị phải khớp
        if field in source_chunk:
            if source_chunk[field] != embedded_chunk_metadata[field]:
                return False
        elif field == "content_type":
            if not embedded_chunk_metadata["content_type"]:
                return False
    return True


class EmbeddedChunk(BaseModel):
    """Đại diện cho một chunk pháp lý đã được nhúng véc-tơ."""
    
    chunk_id: str = Field(..., description="Định danh duy nhất toàn cục của chunk")
    content: str = Field(..., description="Nội dung toàn văn của đoạn pháp lý")
    embedding: List[float] = Field(..., description="Véc-tơ biểu diễn ngữ nghĩa của content")
    metadata: Dict[str, Any] = Field(..., description="Siêu dữ liệu pháp lý (chứa đủ 18 trường bắt buộc)")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True
    )

    @property
    def dimension(self) -> int:
        """Kích thước chiều của vector embedding."""
        return len(self.embedding)

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi sang định dạng dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "embedding": self.embedding,
            "metadata": self.metadata,
        }
