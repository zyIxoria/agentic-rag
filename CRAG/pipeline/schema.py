"""
CRAG Pipeline Schemas.
Định nghĩa cấu trúc dữ liệu phản hồi cho End-to-End Corrective RAG Pipeline.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from RAG.citation.schema import LegalCitation
from RAG.retriever.schema import RetrievedChunk
from CRAG.evaluator.schema import RetrievalGradingResult
from CRAG.refinement.schema import RefinedContext
from CRAG.search.schema import SearchResponse


@dataclass
class CRAGTelemetry:
    """Đo lường chi tiết độ trễ của từng công đoạn trong CRAG Pipeline."""
    retrieval_latency: float = 0.0
    grading_latency: float = 0.0
    refinement_latency: float = 0.0
    transformation_latency: float = 0.0
    search_latency: float = 0.0
    generation_latency: float = 0.0
    total_latency: float = 0.0


@dataclass
class CRAGResponse:
    """Phản hồi đầu ra hoàn chỉnh của hệ thống Corrective RAG."""
    question: str
    answer: str
    citations: List[LegalCitation]
    retrieved_chunks: List[RetrievedChunk]
    grading_result: RetrievalGradingResult
    action_taken: str
    refined_context: Optional[RefinedContext] = None
    search_response: Optional[SearchResponse] = None
    telemetry: CRAGTelemetry = field(default_factory=CRAGTelemetry)
    refused: bool = False
    refusal_reason: Optional[str] = None
