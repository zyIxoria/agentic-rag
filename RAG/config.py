"""config.py - Cấu hình tập trung cho hệ thống Traditional RAG Baseline.

Quản lý các tham số cho:
- Embedding Pipeline (Model, Device, Batch Size, Normalization)
- Fallback an toàn từ GPU/CUDA sang CPU nếu phần cứng hoặc driver không hỗ trợ.
"""

from __future__ import annotations
import os
import logging
from typing import Optional, Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


def resolve_device(requested_device: Optional[str] = None) -> str:
    """Kiểm tra tính khả dụng của GPU/CUDA và tự động fallback về CPU nếu không hỗ trợ.
    
    Args:
        requested_device: Thiết bị được yêu cầu ('cuda', 'gpu', 'cpu', 'auto', None).
        
    Returns:
        'cuda' nếu khả dụng và được yêu cầu, ngược lại 'cpu'.
    """
    if requested_device is None or requested_device.lower() == "auto":
        req = "cuda"
    else:
        req = requested_device.lower().strip()

    if req in ("cuda", "gpu"):
        cuda_available = False
        # Kiểm tra qua torch nếu có
        try:
            import torch
            cuda_available = torch.cuda.is_available()
        except ImportError:
            # Kiểm tra qua onnxruntime nếu có
            try:
                import onnxruntime as ort
                providers = ort.get_available_providers()
                cuda_available = "CUDAExecutionProvider" in providers or "DmlExecutionProvider" in providers
            except ImportError:
                cuda_available = False

        if not cuda_available:
            logger.warning(
                "Device '%s' được yêu cầu nhưng CUDA/GPU runtime không khả dụng hoặc chưa cài đặt driver/wheel tương thích. Tự động fallback về 'cpu'.",
                req
            )
            return "cpu"
        return "cuda"

    return "cpu"


class EmbeddingConfig(BaseSettings):
    """Cấu hình cho phân hệ Embedding theo yêu cầu TASK RAG-01."""

    # 1. Tên định danh mô hình embedding (mặc định all-MiniLM-L6-v2 hoặc BAAI/bge-m3)
    EMBEDDING_MODEL: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Tên hoặc đường dẫn mô hình embedding."
    )

    # 2. Thiết bị tính toán ('cuda', 'cpu', 'auto')
    EMBEDDING_DEVICE: str = Field(
        default="cpu",
        description="Thiết bị thực thi embedding: 'cuda', 'cpu', hoặc 'auto'."
    )

    # 3. Kích thước batch khi sinh vector
    EMBEDDING_BATCH_SIZE: int = Field(
        default=64,
        gt=0,
        description="Kích thước lô xử lý khi embedding hàng loạt."
    )

    # 4. Chuẩn hóa véc-tơ (L2 normalization)
    NORMALIZE_EMBEDDINGS: bool = Field(
        default=True,
        description="Có chuẩn hóa L2 cho các vector embedding trả về hay không."
    )

    # Các trường bổ sung hỗ trợ quản lý
    EMBEDDING_PROVIDER: str = Field(
        default="auto",
        description="Provider sử dụng: 'auto', 'onnx', 'chroma', 'sentence-transformers', 'mock', 'openai'."
    )
    DATASET_PATH: str = Field(
        default="Data_Processing/output_v2/legal_dataset_v2.json",
        description="Đường dẫn tới tệp dữ liệu Legal Dataset V2.1."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("EMBEDDING_DEVICE", mode="after")
    @classmethod
    def validate_device(cls, v: str) -> str:
        """Đảm bảo thiết bị hợp lệ và thực hiện fallback nếu cần."""
        return resolve_device(v)


# Singleton config instance mặc định
default_embedding_config = EmbeddingConfig()
