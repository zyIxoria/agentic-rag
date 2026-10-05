"""pipeline_schema.py - Định nghĩa cấu trúc dữ liệu cho phân hệ tích hợp Traditional RAG Pipeline (TASK RAG-07)."""

from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from RAG.retriever.schema import RetrievedChunk
from RAG.citation.schema import LegalCitation


class RAGResponse(BaseModel):
    """Cấu trúc dữ liệu phản hồi cuối cùng từ toàn bộ chuỗi Traditional RAG Pipeline."""

    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    question: str = Field(..., description="Câu hỏi ban đầu của người dùng")
    answer: str = Field(..., description="Câu trả lời cuối cùng kèm trích dẫn pháp lý hoặc câu từ chối")
    citations: List[LegalCitation] = Field(
        default_factory=list,
        description="Danh sách các đối tượng trích dẫn pháp lý thực tế đã được ánh xạ từ metadata"
    )
    retrieved_chunks: List[RetrievedChunk] = Field(
        default_factory=list,
        description="Danh sách các đoạn văn bản pháp luật thu hồi được từ vector store"
    )
    latency: float = Field(..., description="Tổng thời gian thực thi của toàn chuỗi tính bằng mili-giây (ms)")
    refused: bool = Field(default=False, description="True nếu hệ thống kích hoạt từ chối do thiếu căn cứ")
    refusal_reason: Optional[str] = Field(default=None, description="Lý do chi tiết nếu refused=True")

    # Các trường đo lường độ trễ thành phần
    retrieval_latency: float = Field(default=0.0, description="Thời gian tìm kiếm véc-tơ (ms)")
    context_latency: float = Field(default=0.0, description="Thời gian xây dựng ngữ cảnh và kiểm soát token (ms)")
    generation_latency: float = Field(default=0.0, description="Thời gian sinh câu trả lời của LLM (ms)")
    citation_latency: float = Field(default=0.0, description="Thời gian ánh xạ trích dẫn và kiểm tra guard (ms)")

    # Thông tin thực thi mô hình
    model_name: Optional[str] = Field(default=None, description="Tên mô hình LLM thực thi")
    provider: Optional[str] = Field(default=None, description="Nhà cung cấp LLM ('openai', 'gemini', 'mock')")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata bổ sung cho quá trình thực thi")

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi đối tượng RAGResponse thành từ điển JSON-serializable."""
        return {
            "question": self.question,
            "answer": self.answer,
            "citations": [c.to_dict() for c in self.citations],
            "retrieved_chunks": [c.to_dict() for c in self.retrieved_chunks],
            "latency": self.latency,
            "refused": self.refused,
            "refusal_reason": self.refusal_reason,
            "retrieval_latency": self.retrieval_latency,
            "context_latency": self.context_latency,
            "generation_latency": self.generation_latency,
            "citation_latency": self.citation_latency,
            "model_name": self.model_name,
            "provider": self.provider,
            "metadata": self.metadata,
        }
