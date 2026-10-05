"""
Adaptive RAG Orchestration Schemas.
Định nghĩa cấu trúc dữ liệu cho điều phối luồng thích ứng (Adaptive Orchestration).
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from RAG.retriever.schema import RetrievedChunk
from Adaptive_RAG.classifier.schema import ClassificationResult, RoutingDecision
from Adaptive_RAG.decomposition.schema import DecompositionPlan, SubQuery


class SubQueryExecutionRecord(BaseModel):
    """Ghi nhận kết quả thực thi của một truy vấn con."""
    model_config = ConfigDict(extra="ignore")

    sub_query: SubQuery
    retrieved_chunks: List[RetrievedChunk] = Field(default_factory=list)
    action_taken: str = "RETRIEVAL"
    latency_ms: float = 0.0


class OrchestrationTrace(BaseModel):
    """Dấu vết thực thi toàn diện của bộ điều phối thích ứng."""
    model_config = ConfigDict(extra="ignore")

    query: str
    classification: ClassificationResult
    route_chosen: RoutingDecision
    plan: Optional[DecompositionPlan] = None
    sub_executions: List[SubQueryExecutionRecord] = Field(default_factory=list)
    routing_latency_ms: float = 0.0
    execution_latency_ms: float = 0.0
    synthesis_latency_ms: float = 0.0
    total_latency_ms: float = 0.0


class AdaptiveRAGResponse(BaseModel):
    """Phản hồi đầu ra hoàn chỉnh của hệ thống Adaptive Agentic RAG."""
    model_config = ConfigDict(extra="ignore")

    question: str
    answer: str
    citations: List[Any] = Field(default_factory=list)
    retrieved_chunks: List[RetrievedChunk] = Field(default_factory=list)
    route_taken: RoutingDecision
    classification: ClassificationResult
    trace: OrchestrationTrace
    latency_ms: float = 0.0
    refused: bool = False
    refusal_reason: Optional[str] = None
