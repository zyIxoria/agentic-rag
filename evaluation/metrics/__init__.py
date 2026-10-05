# evaluation/metrics/__init__.py
"""Gói định nghĩa và tính toán các chỉ số đo lường (Metrics) cho đánh giá RAG."""

from evaluation.metrics.answer_metrics import evaluate_answer_correctness
from evaluation.metrics.faithfulness_metrics import evaluate_faithfulness
from evaluation.metrics.citation_metrics import evaluate_citations
from evaluation.metrics.refusal_metrics import evaluate_refusal

__all__ = [
    "evaluate_answer_correctness",
    "evaluate_faithfulness",
    "evaluate_citations",
    "evaluate_refusal",
]
