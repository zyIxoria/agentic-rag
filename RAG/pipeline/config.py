"""config.py - Cấu hình tập trung cho toàn chuỗi Traditional RAG Pipeline."""

from __future__ import annotations
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PipelineConfig(BaseSettings):
    """Cấu hình thực thi cho Traditional RAG Pipeline."""

    # 1. Tham số thu hồi (Retrieval)
    TOP_K: int = Field(
        default=5,
        ge=1,
        description="Số lượng chunks thu hồi từ vector store."
    )
    SIMILARITY_THRESHOLD: float = Field(
        default=0.45,
        ge=0.0,
        le=1.0,
        description="Ngưỡng tương đồng tối thiểu để vượt qua chốt chặn Pre-guard."
    )
    RETRIEVER_TYPE: str = Field(
        default="dense",
        description="Loại bộ thu hồi: 'dense', 'bm25', hoặc 'hybrid' (kết hợp Dense + BM25 + RRF)."
    )
    USE_RERANKER: bool = Field(
        default=False,
        description="Có áp dụng LegalCrossReranker để tái xếp hạng sâu và khử topic drift hay không."
    )

    # 2. Tham số ngữ cảnh (Context Builder)
    MAX_CONTEXT_TOKENS: int = Field(
        default=3000,
        gt=0,
        description="Ngân sách token tối đa cho khối ngữ cảnh cung cấp cho LLM."
    )

    # 3. Tham số mô hình ngôn ngữ (LLM Generation)
    LLM_PROVIDER: str = Field(
        default="auto",
        description="Nhà cung cấp LLM: 'auto', 'gemini', hoặc 'mock'."
    )
    LLM_MODEL: Optional[str] = Field(
        default=None,
        description="Tên mô hình LLM cụ thể (VD: 'gemini-1.5-flash', 'gemini-1.5-pro')."
    )
    TEMPERATURE: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Nhiệt độ sinh mẫu (mặc định 0.0 cho tính tất định tuyệt đối)."
    )

    # 4. Tham số chốt chặn an toàn (Guards)
    ENABLE_PRE_GUARD: bool = Field(
        default=True,
        description="Có bật chốt chặn Pre-generation Guard hay không."
    )
    ENABLE_POST_GUARD: bool = Field(
        default=True,
        description="Có bật chốt chặn Post-generation Guard hay không."
    )

    # 5. Tham số ánh xạ trích dẫn (Citation)
    REPLACE_IN_TEXT_CITATIONS: bool = Field(
        default=True,
        description="Có thay thế trực tiếp thẻ [SOURCE N] trong câu trả lời bằng trích dẫn pháp lý hay không."
    )
    APPEND_FOOTNOTES: bool = Field(
        default=True,
        description="Có đính kèm danh mục tham chiếu phụ lục (Footnotes) ở cuối câu trả lời hay không."
    )

    # 6. Tham số cơ sở dữ liệu véc-tơ
    CHROMA_PERSIST_DIRECTORY: str = Field(
        default="data/chroma_db",
        description="Đường dẫn thư mục lưu trữ ChromaDB."
    )
    COLLECTION_NAME: str = Field(
        default="legal_labor_vietnamese_bi_encoder",
        description="Tên collection véc-tơ mặc định tiếng Việt (768d)."
    )

    # 7. Hệ thống Cờ cấu hình Tính năng Đa tầng (Multi-Tier Safety Feature Flags)
    ENABLE_TIER1_SHARED_SCOPE_GATE: bool = Field(
        default=True,
        description="Bật bộ lọc phạm vi toàn câu tiền truy xuất (Tier 1)."
    )
    ENABLE_TIER2_DOCUMENT_GROUNDING_GATE: bool = Field(
        default=True,
        description="Bật chốt chặn văn bản nguồn chỉ định (Tier 2)."
    )
    ENABLE_TIER3_PRE_GEN_EVIDENCE_GATE: bool = Field(
        default=True,
        description="Bật chốt chặn bằng chứng 5 chiều trước sinh (Tier 3)."
    )
    ENABLE_TIER4_QA_ALIGNMENT_GUARD: bool = Field(
        default=True,
        description="Bật kiểm chứng Claim và trích dẫn sau sinh (Tier 4)."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


default_pipeline_config = PipelineConfig()
