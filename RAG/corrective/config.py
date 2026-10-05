"""config.py - Cấu hình tập trung cho Corrective RAG (CRAG) Pipeline.

Quản lý các tham số:
- Giới hạn retry (MAX_CORRECTIVE_RETRIES = 1)
- Ngưỡng đánh giá (confidence, similarity)
- Mô hình Evaluator và Generator
- Đường dẫn Vector Store và Collection
"""

from __future__ import annotations
from typing import Optional, Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CRAGConfig(BaseSettings):
    """Cấu hình cho Corrective RAG Pipeline."""

    # 1. Tham số Retrieval & Corrective Retry
    TOP_K: int = Field(
        default=5,
        gt=0,
        description="Số lượng chunk thu hồi tối đa mỗi lần retrieval (cố định bằng baseline)."
    )
    SIMILARITY_THRESHOLD: float = Field(
        default=0.45,
        ge=0.0,
        le=1.0,
        description="Ngưỡng tương đồng cosine tối thiểu."
    )
    MAX_CORRECTIVE_RETRIES: int = Field(
        default=1,
        ge=1,
        le=1,
        description="Số lần retry hiệu chỉnh tối đa. Nghiêm ngặt MAX = 1, không retry lần 3."
    )

    # 2. Tham số Retrieval Evaluator
    EVALUATOR_PROVIDER: str = Field(
        default="heuristic",
        description="Provider cho Evaluator: 'heuristic', 'llm', 'mock'."
    )
    EVALUATOR_MODEL: str = Field(
        default="mock-evaluator-v1",
        description="Tên mô hình phục vụ đánh giá tài liệu nếu dùng LLM."
    )
    EVALUATOR_TEMPERATURE: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Nhiệt độ sinh cho Evaluator."
    )
    EVALUATOR_SUFFICIENT_THRESHOLD: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description="Ngưỡng tin cậy tối thiểu để kết luận SUFFICIENT."
    )
    EVALUATOR_PARTIAL_THRESHOLD: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Ngưỡng tin cậy tối thiểu để kết luận PARTIAL."
    )

    # 3. Tham số Query Rewriter
    REWRITER_PROVIDER: str = Field(
        default="rule_based",
        description="Provider cho Query Rewriter: 'rule_based', 'llm', 'mock'."
    )
    REWRITER_MODEL: str = Field(
        default="mock-rewriter-v1",
        description="Tên mô hình viết lại truy vấn nếu dùng LLM."
    )

    # 4. Tham số Generator (Đồng bộ với Baseline)
    LLM_PROVIDER: str = Field(
        default="mock",
        description="Provider cho Generator: 'mock', 'openai', 'gemini'."
    )
    LLM_MODEL: str = Field(
        default="mock-legal-generator-v1",
        description="Tên mô hình cho Generator."
    )
    TEMPERATURE: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Nhiệt độ sinh câu trả lời."
    )
    MAX_CONTEXT_TOKENS: int = Field(
        default=4000,
        gt=0,
        description="Giới hạn dung lượng token của context."
    )

    # 5. Tham số Citation & Guards
    ENABLE_PRE_GUARD: bool = Field(
        default=True,
        description="Bật guard kiểm tra trước khi sinh."
    )
    ENABLE_POST_GUARD: bool = Field(
        default=True,
        description="Bật guard kiểm tra sau khi sinh."
    )
    REPLACE_IN_TEXT_CITATIONS: bool = Field(
        default=True,
        description="Thay thế [SOURCE N] bằng trích dẫn chuẩn hóa."
    )
    APPEND_FOOTNOTES: bool = Field(
        default=False,
        description="Thêm mục trích dẫn cuối văn bản."
    )

    # 6. Tham số Vector Store (Đồng bộ tuyệt đối với Baseline)
    CHROMA_PERSIST_DIRECTORY: str = Field(
        default="data/chroma_db",
        description="Thư mục lưu trữ ChromaDB."
    )
    COLLECTION_NAME: str = Field(
        default="legal_labor_baseline_minilm",
        description="Tên collection véc-tơ chuẩn."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


default_crag_config = CRAGConfig()
