"""factory.py - Hàm tạo (Factory) khởi tạo đối tượng Legal Generator phù hợp."""

from __future__ import annotations
import os
import logging
from typing import Optional

from RAG.generator.base import BaseLegalGenerator
from RAG.generator.openai_generator import OpenAILegalGenerator
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
        provider: 'openai', 'gemini', 'mock', hoặc 'auto' (None).
        model_name: Tên mô hình LLM tương ứng.
        api_key: Khóa API cho cloud provider.
        **kwargs: Tham số bổ sung cho generator.
        
    Returns:
        Instance kế thừa BaseLegalGenerator.
    """
    prov = (provider or os.getenv("LLM_PROVIDER", "auto")).lower().strip()

    if prov == "mock":
        return MockLegalGenerator(model_name=model_name or "mock-legal-generator-v1")

    if prov == "openai":
        return OpenAILegalGenerator(
            model_name=model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            **kwargs
        )

    if prov == "gemini":
        return GeminiLegalGenerator(
            model_name=model_name or os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            api_key=api_key or os.getenv("GEMINI_API_KEY"),
            **kwargs
        )

    if prov in ("auto", "default"):
        # Tự động chọn theo thứ tự ưu tiên: openai -> gemini -> mock
        openai_key = api_key or os.getenv("OPENAI_API_KEY")
        if openai_key and not openai_key.startswith("!"):
            logger.info("Auto-selected OpenAILegalGenerator (gpt-4o-mini).")
            return OpenAILegalGenerator(
                model_name=model_name or "gpt-4o-mini",
                api_key=openai_key,
                **kwargs
            )

        gemini_key = api_key or os.getenv("GEMINI_API_KEY")
        if gemini_key and not gemini_key.startswith("!"):
            logger.info("Auto-selected GeminiLegalGenerator (gemini-1.5-flash).")
            return GeminiLegalGenerator(
                model_name=model_name or "gemini-1.5-flash",
                api_key=gemini_key,
                **kwargs
            )

        logger.info("Không tìm thấy API key hợp lệ trong môi trường. Sử dụng MockLegalGenerator.")
        return MockLegalGenerator(model_name=model_name or "mock-legal-generator-v1")

    raise ValueError(f"Nhà cung cấp LLM không được hỗ trợ: '{prov}'. Chọn 'openai', 'gemini', hoặc 'mock'.")
