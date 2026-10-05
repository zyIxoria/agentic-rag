"""RAG.corrective - Phân hệ Corrective RAG (CRAG) hỗ trợ tra cứu pháp luật lao động Việt Nam."""

from RAG.corrective.schemas import (
    EvaluationStatus,
    RetrievalEvaluation,
    CRAGResponse,
)
from RAG.corrective.config import CRAGConfig, default_crag_config
from RAG.corrective.evaluator import RetrievalEvaluator
from RAG.corrective.rewriter import QueryRewriter
from RAG.corrective.corrective_rag import CorrectiveRAGPipeline

__all__ = [
    "EvaluationStatus",
    "RetrievalEvaluation",
    "CRAGResponse",
    "CRAGConfig",
    "default_crag_config",
    "RetrievalEvaluator",
    "QueryRewriter",
    "CorrectiveRAGPipeline",
]
