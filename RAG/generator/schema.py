"""schema.py - Định nghĩa cấu trúc dữ liệu cho phân hệ Generator (RAG-05)."""

from __future__ import annotations
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class LegalAnswer(BaseModel):
    """Cấu trúc dữ liệu đầu ra có cấu trúc (Structured Output) từ LLM Generator."""
    
    model_config = ConfigDict(extra="ignore")

    answer: str = Field(
        ...,
        description="Nội dung câu trả lời bằng tiếng Việt, trích dẫn rõ [SOURCE N] hoặc câu từ chối chuẩn."
    )
    citations: List[str] = Field(
        default_factory=list,
        description="Danh sách định danh các nguồn được trích dẫn (ví dụ: ['SOURCE 1', 'SOURCE 2'])."
    )
    refused: bool = Field(
        default=False,
        description="True nếu không tìm thấy đủ căn cứ pháp lý trong ngữ cảnh được cung cấp."
    )
    reason: Optional[str] = Field(
        default=None,
        description="Lý do từ chối nếu refused=True hoặc thông tin ghi chú nội bộ."
    )


class GenerationRequest(BaseModel):
    """Yêu cầu sinh câu trả lời gửi tới Generator."""
    
    model_config = ConfigDict(extra="ignore")

    question: str = Field(..., description="Câu hỏi của người dùng.")
    context: str = Field(..., description="Ngữ cảnh có cấu trúc được xây dựng từ Context Builder.")
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Nhiệt độ sinh mẫu (mặc định 0.0 cho tính tất định)."
    )
    max_tokens: int = Field(
        default=1024,
        gt=0,
        description="Số lượng token tối đa cho câu trả lời."
    )


class GenerationResult(BaseModel):
    """Kết quả toàn diện từ Generator bao gồm cả metadata thực thi."""
    
    model_config = ConfigDict(extra="ignore")

    answer: str = Field(..., description="Nội dung câu trả lời.")
    citations: List[str] = Field(default_factory=list, description="Danh sách các nguồn được trích dẫn.")
    refused: bool = Field(default=False, description="Trạng thái từ chối do thiếu căn cứ.")
    reason: Optional[str] = Field(default=None, description="Lý do từ chối nếu có.")
    raw_response: Optional[str] = Field(default=None, description="Chuỗi phản hồi thô từ LLM.")
    model_name: str = Field(..., description="Tên mô hình LLM đã thực hiện sinh.")
    provider: str = Field(..., description="Nhà cung cấp ('openai', 'gemini', 'mock').")
    latency_ms: Optional[float] = Field(default=None, description="Thời gian thực thi tính bằng mili-giây.")

    def to_legal_answer(self) -> LegalAnswer:
        """Chuyển đổi về dạng LegalAnswer thuần túy."""
        return LegalAnswer(
            answer=self.answer,
            citations=self.citations,
            refused=self.refused,
            reason=self.reason
        )
