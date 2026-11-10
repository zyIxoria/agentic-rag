"""RAG/guards/__init__.py - Phân hệ chốt chặn an toàn và kiểm soát bằng chứng đa tầng."""

from RAG.guards.config import GuardConfig, default_guard_config
from RAG.guards.refusal_guard import RefusalGuard, GuardCheckResult
from RAG.guards.scope_guard import SharedScopeGuard, ScopeCheckResult
from RAG.guards.document_grounding_gate import NamedLegalDocumentResolver, DocumentGroundingResult
from RAG.guards.evidence_gate import PreGenerationEvidenceGate, EvidenceGradingReport, ChunkGrade
from RAG.guards.qa_alignment_guard import PostGenerationQAAlignmentGuard, QAAlignmentResult

__all__ = [
    "GuardConfig",
    "default_guard_config",
    "RefusalGuard",
    "GuardCheckResult",
    "SharedScopeGuard",
    "ScopeCheckResult",
    "NamedLegalDocumentResolver",
    "DocumentGroundingResult",
    "PreGenerationEvidenceGate",
    "EvidenceGradingReport",
    "ChunkGrade",
    "PostGenerationQAAlignmentGuard",
    "QAAlignmentResult",
]
