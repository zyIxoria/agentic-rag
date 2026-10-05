"""schema.py - Schema dữ liệu đánh giá toàn diện cho Traditional RAG (TASK RAG-10)."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SingleEvaluationRecord(BaseModel):
    """Bản ghi kết quả đánh giá cho một câu hỏi trong benchmark."""
    question_id: str
    question: str
    category: str
    requires_refusal: bool
    refused: bool
    refusal_reason: Optional[str] = None
    
    # Câu trả lời và trích dẫn
    generated_answer: str
    reference_answer: str
    citations: List[Any] = Field(default_factory=list)
    retrieved_chunk_ids: List[str] = Field(default_factory=list)
    gold_chunk_ids: List[str] = Field(default_factory=list)
    gold_articles: List[str] = Field(default_factory=list)
    
    # Metrics
    answer_correctness: Dict[str, Any]
    faithfulness: Dict[str, Any]
    citation_metrics: Dict[str, Any]
    refusal_metrics: Dict[str, Any]
    
    # Latencies (ms)
    retrieval_latency_ms: float
    context_latency_ms: float
    generation_latency_ms: float
    citation_latency_ms: float
    total_latency_ms: float
    
    # Tokens
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    
    # Phân loại lỗi (nếu có)
    error_type: Optional[str] = None
    error_details: Optional[str] = None


class CategoryMetrics(BaseModel):
    """Chỉ số tổng hợp theo danh mục."""
    category: str
    count: int
    answer_correctness_rate: float
    faithfulness_rate: float
    unsupported_claim_rate: float
    citation_accuracy: float
    citation_coverage: float
    refusal_accuracy: float
    false_refusal_rate: float
    false_answer_rate: float
    mean_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
