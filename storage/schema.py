"""storage/schema.py - Định nghĩa Schema dữ liệu cho hệ thống lưu trữ lịch sử truy vấn."""

from __future__ import annotations
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CitationItem(BaseModel):
    """Thông tin một trích dẫn căn cứ pháp lý."""
    document_title: Optional[str] = None
    document_number: Optional[str] = None
    article_number: Optional[str] = None
    clause_number: Optional[str] = None
    point_number: Optional[str] = None
    source_url: Optional[str] = None
    formatted_citation: Optional[str] = None
    is_valid: bool = True


class RetrievedChunkItem(BaseModel):
    """Thông tin một đoạn văn bản (chunk) được truy xuất."""
    chunk_id: str
    score: float = 0.0
    document_id: Optional[str] = None
    article_number: Optional[str] = None
    content_snippet: Optional[str] = None


class QueryHistoryRecord(BaseModel):
    """Bản ghi chi tiết một phiên hỏi đáp pháp luật trong cơ sở dữ liệu."""
    id: Optional[int] = None
    session_id: Optional[str] = Field(default=None, description="Mã định danh phiên chat/người dùng")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Thời điểm truy vấn (UTC ISO-8601)"
    )
    model_name: str = Field(description="Tên mô hình: Traditional-RAG, CRAG, Adaptive-Agentic-RAG")
    provider: str = Field(default="mock", description="LLM Provider: mock, openai, gemini...")
    query: str = Field(description="Nội dung câu hỏi của người dùng")
    
    # Metadata điều phối & phân loại (CRAG & Adaptive RAG)
    intent: Optional[str] = Field(default=None, description="Ý định câu hỏi (LEGAL_DIRECT_DEF, LEGAL_MULTI_DOC...)")
    complexity: Optional[str] = Field(default=None, description="Độ phức tạp (SIMPLE_SINGLE_HOP, COMPLEX_MULTI_HOP...)")
    route_taken: Optional[str] = Field(default=None, description="Nhánh xử lý: DIRECT_ANSWER, CORRECTIVE_RAG, DECOMPOSE_AGENTIC...")
    routing_reason: Optional[str] = Field(default=None, description="Lý do bộ điều phối chọn nhánh")
    
    # Kết quả câu trả lời
    answer: str = Field(description="Câu trả lời pháp lý được sinh ra")
    citations: List[Dict[str, Any]] = Field(default_factory=list, description="Danh sách trích dẫn căn cứ pháp lý")
    retrieved_chunks: List[Dict[str, Any]] = Field(default_factory=list, description="Danh sách chunk ID và điểm truy xuất")
    sub_queries: List[str] = Field(default_factory=list, description="Các câu hỏi con sau phân rã (nếu có)")
    
    # Trạng thái từ chối & an toàn
    is_refused: bool = Field(default=False, description="Hệ thống có từ chối trả lời do thiếu căn cứ không")
    refusal_reason: Optional[str] = Field(default=None, description="Lý do từ chối nếu có")
    
    # Đo lường vận hành (Telemetry)
    retrieval_latency_ms: float = Field(default=0.0, description="Độ trễ truy xuất (ms)")
    generation_latency_ms: float = Field(default=0.0, description="Độ trễ sinh mẫu (ms)")
    total_latency_ms: float = Field(default=0.0, description="Tổng độ trễ xử lý (ms)")
    
    # Tokens & Chi phí ước tính
    input_tokens: int = Field(default=0, description="Số lượng input tokens ước tính")
    output_tokens: int = Field(default=0, description="Số lượng output tokens ước tính")
    total_tokens: int = Field(default=0, description="Tổng số tokens")
    estimated_cost_usd: float = Field(default=0.0, description="Chi phí quy đổi USD ước tính (GPT-4o-mini chuẩn)")
    
    # Đánh giá của người dùng (Feedback loop)
    user_rating: Optional[int] = Field(default=None, description="Đánh giá người dùng (-1: dislike, 1: like, hoặc 1-5)")
    user_feedback: Optional[str] = Field(default=None, description="Góp ý phản hồi của người dùng")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata mở rộng khác")


class HistoryFilter(BaseModel):
    """Bộ lọc tìm kiếm lịch sử truy vấn."""
    session_id: Optional[str] = None
    model_name: Optional[str] = None
    route_taken: Optional[str] = None
    is_refused: Optional[bool] = None
    search_keyword: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    limit: int = 50
    offset: int = 0


class HistoryStatistics(BaseModel):
    """Thống kê tổng hợp toàn bộ lịch sử truy vấn."""
    total_queries: int = 0
    total_refusals: int = 0
    refusal_rate: float = 0.0
    queries_by_model: Dict[str, int] = Field(default_factory=dict)
    queries_by_route: Dict[str, int] = Field(default_factory=dict)
    avg_total_latency_ms: float = 0.0
    avg_total_tokens: float = 0.0
    total_estimated_cost_usd: float = 0.0
    feedback_stats: Dict[str, int] = Field(default_factory=dict)
