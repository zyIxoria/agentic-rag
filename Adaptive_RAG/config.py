"""config.py - Cấu hình tập trung cho Adaptive Agentic RAG Framework."""

from __future__ import annotations
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AdaptiveRAGConfig(BaseSettings):
    """Cấu hình vận hành cho hệ thống Adaptive Agentic RAG."""

    # 1. Cấu hình Classifier
    CLASSIFIER_TYPE: Literal["hybrid", "rule_based", "llm", "auto"] = Field(
        default="hybrid",
        description="Động cơ phân loại độ phức tạp: 'hybrid' (kết hợp quy tắc thực thể + ngữ nghĩa), 'llm', 'auto'."
    )
    COMPLEXITY_CONFIDENCE_THRESHOLD: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description="Ngưỡng độ tin cậy để phân định câu hỏi phức tạp đa chặng."
    )

    # 2. Cấu hình Query Decomposition
    MAX_SUB_QUERIES: int = Field(
        default=4,
        gt=0,
        le=6,
        description="Số lượng truy vấn con tối đa được phân rã từ một câu hỏi phức tạp."
    )
    MIN_DECOMPOSITION_LENGTH: int = Field(
        default=15,
        gt=0,
        description="Độ dài tối thiểu của câu hỏi để xem xét phân rã."
    )

    # 3. Cấu hình Adaptive Routing
    ENABLE_DIRECT_ROUTING: bool = Field(
        default=True,
        description="Bật điều phối trực tiếp (Direct Routing) cho câu hỏi chào hỏi hoặc ngoài phạm vi (tiết kiệm 100% chi phí retrieval)."
    )
    ENABLE_SUBQUERY_PARALLELISM: bool = Field(
        default=True,
        description="Cho phép thực thi các sub-queries độc lập song song."
    )
    FALLBACK_TO_CRAG_ON_UNCERTAINTY: bool = Field(
        default=True,
        description="Tự động chuyển tiếp sang luồng CRAG nếu kết quả tổng hợp có độ tin cậy thấp."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Singleton instance mặc định
default_adaptive_config = AdaptiveRAGConfig()
adaptive_config = default_adaptive_config
