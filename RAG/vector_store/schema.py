"""schema.py - Cấu trúc dữ liệu và định nghĩa bản ghi véc-tơ cho Vector Store.

Tuân thủ nghiêm ngặt Data Model của TASK RAG-02:
- id: chunk_id từ Dataset V2.1
- embedding: vector biểu diễn ngữ nghĩa
- document: content nội dung pháp lý
- metadata: toàn bộ siêu dữ liệu pháp lý (21 trường chuẩn)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone


# Các trường metadata được coi là null khi có giá trị chuỗi rỗng
NULL_STRING_SENTINEL = ""
EMPTY_METADATA_SENTINEL = "_empty"


def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Union[str, int, float, bool]]:
    """Chuyển đổi metadata sang định dạng tương thích 100% với ChromaDB.
    
    ChromaDB yêu cầu kiểu giá trị metadata phải là: str, int, float, hoặc bool
    và không cho phép dictionary rỗng {}.
    
    Args:
        metadata: Dictionary siêu dữ liệu thô.
        
    Returns:
        Dictionary chứa các giá trị hợp lệ với ChromaDB.
    """
    if not metadata:
        return {EMPTY_METADATA_SENTINEL: True}

    sanitized: Dict[str, Union[str, int, float, bool]] = {}
    for key, value in metadata.items():
        if value is None:
            sanitized[key] = NULL_STRING_SENTINEL
        elif isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        else:
            sanitized[key] = str(value)
    return sanitized


def desanitize_metadata(
    metadata: Dict[str, Any],
    restore_none: bool = True
) -> Dict[str, Any]:
    """Khôi phục metadata từ ChromaDB về dạng nguyên bản (bao gồm các giá trị None).
    
    Args:
        metadata: Dictionary metadata lấy từ ChromaDB.
        restore_none: Nếu True, chuyển đổi chuỗi rỗng "" trở lại thành None.
        
    Returns:
        Dictionary siêu dữ liệu nguyên bản.
    """
    if metadata.get(EMPTY_METADATA_SENTINEL) is True and len(metadata) == 1:
        return {}

    restored: Dict[str, Any] = {}
    for key, value in metadata.items():
        if key == EMPTY_METADATA_SENTINEL:
            continue
        if restore_none and value == NULL_STRING_SENTINEL:
            restored[key] = None
        else:
            restored[key] = value
    return restored



@dataclass
class VectorRecord:
    """Mô hình dữ liệu cho một bản ghi véc-tơ đơn lẻ."""
    id: str
    embedding: List[float]
    document: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id or not str(self.id).strip():
            raise ValueError("Trường 'id' (chunk_id) không được để trống.")
        if not isinstance(self.embedding, list):
            raise TypeError("Trường 'embedding' phải là một danh sách float (List[float]).")
        if not self.document:
            raise ValueError("Trường 'document' (content) không được để trống.")

    @classmethod
    def from_dict(cls, data: Dict[str, Any], embedding: List[float]) -> VectorRecord:
        """Tạo VectorRecord từ dictionary bản ghi của Dataset V2.1."""
        chunk_id = str(data["chunk_id"])
        document = str(data["content"])
        metadata = {k: v for k, v in data.items() if k not in ("chunk_id", "content")}
        return cls(id=chunk_id, embedding=embedding, document=document, metadata=metadata)


@dataclass
class CollectionConfig:
    """Cấu hình và siêu dữ liệu kiểm soát an toàn của Collection."""
    dataset_version: str
    embedding_model: str
    embedding_dimension: int
    distance_metric: str = "cosine"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    description: Optional[str] = None

    extra: Dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> Dict[str, Union[str, int, float, bool]]:
        """Xuất metadata cho collection của ChromaDB."""
        meta: Dict[str, Union[str, int, float, bool]] = {
            "dataset_version": self.dataset_version,
            "embedding_model": self.embedding_model,
            "embedding_dimension": int(self.embedding_dimension),
            "hnsw:space": self.distance_metric,
            "created_at": self.created_at,
        }
        if self.description:
            meta["description"] = self.description
        for k, v in self.extra.items():
            if isinstance(v, (str, int, float, bool)):
                meta[k] = v
        return meta

    @classmethod
    def from_metadata(cls, meta: Dict[str, Any]) -> CollectionConfig:
        """Khởi tạo cấu hình từ metadata của collection trong ChromaDB."""
        return cls(
            dataset_version=str(meta.get("dataset_version", "unknown")),
            embedding_model=str(meta.get("embedding_model", "unknown")),
            embedding_dimension=int(meta.get("embedding_dimension", 0)),
            distance_metric=str(meta.get("hnsw:space", "cosine")),
            created_at=str(meta.get("created_at", "")),
            description=meta.get("description"),
            extra={k: v for k, v in meta.items() if k not in (
                "dataset_version", "embedding_model", "embedding_dimension",
                "hnsw:space", "created_at", "description"
            )}
        )
