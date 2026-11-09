"""factory.py - Hàm tạo (Factory) khởi tạo đối tượng Legal Generator phù hợp (Google Gemini & Mock)."""

from __future__ import annotations
import os
import logging
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except Exception:
    pass

from RAG.generator.base import BaseLegalGenerator
from RAG.generator.gemini_generator import GeminiLegalGenerator
from RAG.generator.mock_generator import MockLegalGenerator

logger = logging.getLogger(__name__)


def get_generator(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs
) -> BaseLegalGenerator:
    """Khởi tạo và trả về đối tượng Legal Generator thích hợp.
    
    Args:
        provider: 'gemini', 'mock', hoặc 'auto' (None).
        model_name: Tên mô hình LLM tương ứng (mặc định gemini-1.5-flash).
        api_key: Khóa API cho cloud provider Gemini.
        **kwargs: Tham số bổ sung cho generator.
        
    Returns:
        Instance kế thừa BaseLegalGenerator.
    """
    prov = (provider or os.getenv("LLM_PROVIDER", "auto")).lower().strip()

    if prov == "mock":
        return MockLegalGenerator(model_name=model_name or "mock-legal-generator-v1")

    if prov == "gemini":
        return GeminiLegalGenerator(
            model_name=model_name or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
            api_key=api_key or os.getenv("GEMINI_API_KEY"),
            **kwargs
        )

    if prov in ("auto", "default"):
        # Tự động chọn: nếu có GEMINI_API_KEY thì kích hoạt Gemini, ngược lại fallback về Mock
        gemini_key = api_key or os.getenv("GEMINI_API_KEY")
        if gemini_key and not gemini_key.startswith("!"):
            logger.info("Auto-selected GeminiLegalGenerator (gemini-3.5-flash-lite).")
            return GeminiLegalGenerator(
                model_name=model_name or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
                api_key=gemini_key,
                **kwargs
            )

        logger.info("Không tìm thấy GEMINI_API_KEY trong môi trường. Sử dụng MockLegalGenerator.")
        return MockLegalGenerator(model_name=model_name or "mock-legal-generator-v1")

    if prov == "openai":
        raise ValueError("Nhà cung cấp OpenAI đã bị vô hiệu hóa trong hệ thống. Vui lòng chuyển sang 'gemini' hoặc 'mock'.")

    raise ValueError(f"Nhà cung cấp LLM không được hỗ trợ: '{prov}'. Chọn 'gemini' hoặc 'mock'.")
