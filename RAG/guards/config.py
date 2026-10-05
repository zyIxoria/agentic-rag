"""config.py - Cấu hình cho phân hệ chốt chặn an toàn và từ chối (Refusal Guard)."""

from __future__ import annotations
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from RAG.prompts.legal_prompts import STANDARD_REFUSAL_ANSWER


class GuardConfig(BaseSettings):
    """Cấu hình cho Refusal Guard."""

    # Ngưỡng tương đồng tối thiểu để vượt qua chốt chặn Pre-generation
    SIMILARITY_THRESHOLD: float = Field(
        default=0.45,
        ge=0.0,
        le=1.0,
        description="Ngưỡng tương đồng tối thiểu của chunk rank 1 để cho phép chuyển sang LLM sinh câu trả lời."
    )

    # Số lượng chunk tối thiểu cần có
    MIN_RETRIEVED_CHUNKS: int = Field(
        default=1,
        ge=1,
        description="Số lượng chunk thu hồi tối thiểu."
    )

    # Bật/tắt chốt chặn trước khi sinh (Pre-generation guard)
    ENABLE_PRE_GENERATION_GUARD: bool = Field(
        default=True,
        description="Có chặn sớm trước khi gọi LLM khi retrieval rỗng hoặc điểm thấp không."
    )

    # Bật/tắt chốt chặn sau khi sinh (Post-generation guard)
    ENABLE_POST_GENERATION_GUARD: bool = Field(
        default=True,
        description="Có kiểm tra trích dẫn và tính nhất quán sau khi LLM sinh không."
    )

    # Từ chối nếu toàn bộ trích dẫn là invalid
    REJECT_UNSUPPORTED_ANSWERS: bool = Field(
        default=True,
        description="Có tự động chuyển sang từ chối nếu toàn bộ trích dẫn của LLM là giả mạo/invalid không."
    )

    # Chuỗi từ chối chuẩn mực
    REFUSAL_MESSAGE: str = Field(
        default=STANDARD_REFUSAL_ANSWER,
        description="Thông báo từ chối bắt buộc khi thiếu căn cứ pháp lý."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


default_guard_config = GuardConfig()
