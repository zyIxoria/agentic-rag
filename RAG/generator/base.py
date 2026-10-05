"""base.py - Lớp cơ sở trừu tượng cho Legal Generator."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
from RAG.generator.schema import GenerationRequest, GenerationResult


class BaseLegalGenerator(ABC):
    """Giao diện chung cho các bộ sinh câu trả lời Traditional RAG."""

    @abstractmethod
    def generate_structured(self, request: GenerationRequest) -> GenerationResult:
        """Sinh câu trả lời có cấu trúc từ GenerationRequest.
        
        Args:
            request: Đối tượng yêu cầu chứa question, context, temperature, max_tokens.
            
        Returns:
            GenerationResult chứa answer, citations, refused, reason, metadata.
        """
        pass

    def generate(
        self,
        question: str,
        context: str,
        temperature: float = 0.0,
        max_tokens: int = 1024
    ) -> GenerationResult:
        """Phương thức tiện ích sinh câu trả lời từ tham số rời rạc.
        
        Args:
            question: Câu hỏi người dùng.
            context: Ngữ cảnh có cấu trúc đã dựng từ RAG-04.
            temperature: Nhiệt độ sinh (mặc định 0.0).
            max_tokens: Số token tối đa.
            
        Returns:
            GenerationResult.
        """
        request = GenerationRequest(
            question=question,
            context=context,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return self.generate_structured(request)
