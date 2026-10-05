"""config.py - Cấu hình cho phân hệ Legal Context Builder (TASK RAG-04)."""

from __future__ import annotations
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ContextConfig(BaseSettings):
    """Cấu hình quản lý đóng gói ngữ cảnh cho LLM."""

    # 1. Ngưỡng trần số lượng tokens tối đa cho toàn bộ Context (đóng băng tại RAG-00: 3000 tokens)
    MAX_CONTEXT_TOKENS: int = Field(
        default=3000,
        gt=0,
        description="Ngân sách token tối đa cho context được nạp vào LLM."
    )

    # 2. Hệ số ước tính BPE subword tokens trên từ tiếng Việt (đồng bộ config_v2.py)
    TOKEN_MULTIPLIER: float = Field(
        default=1.3,
        gt=0.0,
        description="Hệ số chuyển đổi từ (word count) sang token tiếng Việt."
    )

    # 3. Ký tự phân cách giữa các nguồn trong context
    SOURCE_SEPARATOR: str = Field(
        default="\n\n---\n\n",
        description="Chuỗi ký tự phân tách giữa các khối nguồn [SOURCE X]."
    )

    # 4. Thông điệp khi không có nguồn nào được thu hồi hoặc vượt ngưỡng lọc
    EMPTY_CONTEXT_MESSAGE: str = Field(
        default="Không có ngữ cảnh tài liệu pháp lý nào được thu hồi.",
        description="Chuỗi thông báo khi context rỗng."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Singleton config instance mặc định
default_context_config = ContextConfig()
