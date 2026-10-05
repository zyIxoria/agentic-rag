"""
Adaptive RAG Classifier Package.
Phân hệ phân loại độ phức tạp và ý định câu hỏi (Module 0).
"""

from Adaptive_RAG.classifier.schema import (
    # Chuẩn mới Module 0
    ComplexityClass,
    RoutingStrategy,
    QueryComplexityFeatures,
    QueryComplexityResult,
    # Legacy
    QueryIntent,
    ComplexityLevel,
    RoutingDecision,
    ClassificationResult,
)
from Adaptive_RAG.classifier.base import BaseQueryClassifier
from Adaptive_RAG.classifier.hybrid_classifier import HybridQueryClassifier
from Adaptive_RAG.classifier.query_complexity_classifier import QueryComplexityClassifier

__all__ = [
    # Module 0
    "ComplexityClass",
    "RoutingStrategy",
    "QueryComplexityFeatures",
    "QueryComplexityResult",
    "QueryComplexityClassifier",
    # Legacy
    "QueryIntent",
    "ComplexityLevel",
    "RoutingDecision",
    "ClassificationResult",
    "BaseQueryClassifier",
    "HybridQueryClassifier",
]
