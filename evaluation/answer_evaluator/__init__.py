# evaluation/answer_evaluator/__init__.py
"""Gói đánh giá câu trả lời Legal Answer Evaluator."""

from evaluation.answer_evaluator.schema import SingleEvaluationRecord, CategoryMetrics
from evaluation.answer_evaluator.evaluator import LegalAnswerEvaluator

__all__ = [
    "SingleEvaluationRecord",
    "CategoryMetrics",
    "LegalAnswerEvaluator",
]
