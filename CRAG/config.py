"""config.py - Cấu hình tập trung cho Corrective RAG (CRAG) Framework."""

from __future__ import annotations
from typing import Optional, Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CRAGConfig(BaseSettings):
    """Cấu hình vận hành cho hệ thống Corrective RAG (CRAG)."""

    # 1. Ngưỡng phân loại của Retrieval Evaluator (Document Grader)
    UPPER_THRESHOLD: float = Field(
        default=0.68,
        ge=0.0,
        le=1.0,
        description="Ngưỡng tin cậy trên: Điểm >= UPPER_THRESHOLD được đánh giá là CORRECT (Phù hợp)."
    )
    LOWER_THRESHOLD: float = Field(
        default=0.45,
        ge=0.0,
        le=1.0,
        description="Ngưỡng tin cậy dưới: Điểm < LOWER_THRESHOLD được đánh giá là INCORRECT (Lạc đề/Không phù hợp)."
    )

    # 2. Loại Document Grader sử dụng ('semantic', 'llm', 'rule_based', 'auto')
    GRADER_TYPE: Literal["semantic", "llm", "rule_based", "auto"] = Field(
        default="auto",
        description="Động cơ đánh giá tài liệu: 'semantic' (tính toán ngữ nghĩa + thực thể), 'llm', 'auto'."
    )

    # 3. Tham số Knowledge Refinement (Decompose, Strip & Filter)
    STRIP_THRESHOLD: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Ngưỡng tối thiểu để giữ lại một đoạn tri thức (Knowledge Strip) sau khi phân mảnh chunk."
    )
    MAX_REFINED_STRIPS: int = Field(
        default=6,
        gt=0,
        description="Số lượng strip tri thức tối đa được chọn lọc để tái cấu trúc ngữ cảnh."
    )

    # 4. Tham số Web Search Fallback
    SEARCH_PROVIDER: Literal["mock", "duckduckgo", "auto"] = Field(
        default="auto",
        description="Engine tìm kiếm ngoài khi kích hoạt fallback: 'mock' (offline), 'duckduckgo', 'auto'."
    )
    MAX_SEARCH_RESULTS: int = Field(
        default=3,
        gt=0,
        description="Số lượng kết quả tìm kiếm ngoài tối đa được lấy về."
    )

    MAX_REFINED_CONTEXT_CHARS: int = Field(
        default=3500,
        gt=0,
        description="Độ dài ký tự tối đa của ngữ cảnh tinh lọc sau khi tái hợp."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("LOWER_THRESHOLD")
    @classmethod
    def validate_thresholds(cls, v: float, info) -> float:
        upper = info.data.get("UPPER_THRESHOLD", 0.68)
        if v >= upper:
            raise ValueError(f"LOWER_THRESHOLD ({v}) phải nhỏ hơn UPPER_THRESHOLD ({upper}).")
        return v


# Singleton instance mặc định
default_crag_config = CRAGConfig()
crag_config = default_crag_config
