"""config.py - Cấu hình cho phân hệ Dense Semantic Retrieval (TASK RAG-03).

Quản lý các tham số:
- TOP_K: Số lượng kết quả thu hồi mặc định.
- SIMILARITY_THRESHOLD: Ngưỡng điểm tương đồng tối thiểu để giữ lại chunk.
- PERSIST_DIRECTORY & COLLECTION_NAME: Vị trí và tên collection Vector Store.
"""

from __future__ import annotations
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RetrieverConfig(BaseSettings):
    """Cấu hình cho DenseTopKRetriever."""

    # 1. Số lượng chunk thu hồi mặc định (không hard-code)
    TOP_K: int = Field(
        default=5,
        gt=0,
        description="Số lượng chunks tối đa được thu hồi (Top-K)."
    )

    # 2. Ngưỡng điểm tương đồng (tùy chọn, None nếu không lọc)
    SIMILARITY_THRESHOLD: Optional[float] = Field(
        default=None,
        description="Ngưỡng Cosine Similarity tối thiểu (-1.0 đến 1.0). Nếu None, không lọc ngưỡng."
    )

    # 3. Đường dẫn lưu trữ Vector DB
    PERSIST_DIRECTORY: str = Field(
        default="data/chroma_db",
        description="Thư mục lưu trữ cơ sở dữ liệu véc-tơ bền vững."
    )

    # 4. Tên Collection ChromaDB liên kết
    COLLECTION_NAME: str = Field(
        default="legal_labor_baseline_minilm",
        description="Tên collection chứa vector embeddings của Dataset V2.1."
    )

    # 5. Phép đo khoảng cách
    DISTANCE_METRIC: str = Field(
        default="cosine",
        description="Phép đo khoảng cách của Vector DB (cosine, l2, ip)."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("SIMILARITY_THRESHOLD")
    @classmethod
    def validate_threshold(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (-1.0 <= v <= 1.0):
            raise ValueError(f"SIMILARITY_THRESHOLD phải nằm trong khoảng [-1.0, 1.0], nhận được: {v}")
        return v


# Singleton instance mặc định
default_retriever_config = RetrieverConfig()
