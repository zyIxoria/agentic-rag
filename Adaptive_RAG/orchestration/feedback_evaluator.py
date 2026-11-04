"""
Post-Retrieval Confidence Evaluator and Dynamic Feedback Loop.
Đánh giá độ tin cậy và mức độ liên quan của tập chunks sau khi truy xuất (Post-Retrieval Confidence Evaluation),
tự động quyết định Nâng cấp luồng (Escalation) từ TRADITIONAL_RAG sang CORRECTIVE_RAG/DECOMPOSE_AGENTIC
hoặc kích hoạt Web Search Fallback cho các sub-query bị thiếu điều luật.
"""

from __future__ import annotations
import logging
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

from RAG.retriever.schema import RetrievedChunk
from CRAG.evaluator.semantic_grader import SemanticDocumentGrader
from CRAG.evaluator.schema import GradeVerdict, RetrievalGradingResult
from CRAG.config import CRAGConfig

logger = logging.getLogger(__name__)


class ConfidenceLevel(str, Enum):
    """Mức độ tin cậy của tập dữ liệu sau khi truy xuất."""
    HIGH = "HIGH"              # Rất tin cậy: Có ít nhất 1 chunk khớp chính xác điều luật và chủ đề
    AMBIGUOUS = "AMBIGUOUS"    # Lơ lửng: Điểm tương đồng trung bình, có thể dính nhiễu hoặc mâu thuẫn
    LOW = "LOW"                # Kém tin cậy: Toàn bộ chunk lạc đề hoặc điểm tương đồng quá thấp (< threshold)
    EMPTY = "EMPTY"            # Rỗng: Không thu hồi được bất kỳ chunk nào


class EscalationTarget(str, Enum):
    """Mục tiêu nâng cấp luồng xử lý phản hồi 2 chiều."""
    NONE = "NONE"                                      # Không nâng cấp, tiếp tục sinh câu trả lời
    ESCALATE_TO_CRAG = "ESCALATE_TO_CRAG"              # Nâng cấp sang CRAG (lọc strip tri thức & web search)
    ESCALATE_TO_DECOMPOSE = "ESCALATE_TO_DECOMPOSE"    # Nâng cấp sang Decompose Agentic (bẻ nhỏ đa chặng)
    WEB_SEARCH_SUBQUERY = "WEB_SEARCH_SUBQUERY"        # Kích hoạt Web Search riêng cho sub-query thiếu luật


class PostRetrievalEvaluation(BaseModel):
    """Kết quả đánh giá độ tin cậy sau truy xuất."""
    model_config = ConfigDict(extra="ignore")

    confidence_level: ConfidenceLevel
    overall_score: float = 0.0
    num_chunks: int = 0
    num_relevant: int = 0
    recommended_action: EscalationTarget = EscalationTarget.NONE
    reason: str = ""
    grading_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence_level": self.confidence_level.value,
            "overall_score": self.overall_score,
            "num_chunks": self.num_chunks,
            "num_relevant": self.num_relevant,
            "recommended_action": self.recommended_action.value,
            "reason": self.reason,
        }


class PostRetrievalConfidenceEvaluator:
    """
    Bộ đánh giá phản hồi 2 chiều (Dynamic Feedback Evaluator):
    Đóng vai trò 'Chốt kiểm định chất lượng' (Quality Gate) ngay sau bước Dense Retrieval.
    Ngăn chặn tuyệt đối việc chuyển tiếp các tài liệu rác/lạc đề vào Generator.
    """

    def __init__(self, crag_cfg: Optional[CRAGConfig] = None):
        self.grader = SemanticDocumentGrader(config=crag_cfg)
        self.upper_threshold = self.grader.config.UPPER_THRESHOLD
        self.lower_threshold = self.grader.config.LOWER_THRESHOLD

    def evaluate(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        is_multi_hop_query: bool = False,
    ) -> PostRetrievalEvaluation:
        """
        Đánh giá độ tin cậy sau truy xuất cho một tập chunks.
        """
        if not chunks or len(chunks) == 0:
            target = EscalationTarget.ESCALATE_TO_DECOMPOSE if is_multi_hop_query else EscalationTarget.ESCALATE_TO_CRAG
            return PostRetrievalEvaluation(
                confidence_level=ConfidenceLevel.EMPTY,
                overall_score=0.0,
                num_chunks=0,
                num_relevant=0,
                recommended_action=target,
                reason="Tập kết quả truy xuất rỗng (0 chunks), cần nâng cấp luồng xử lý sâu.",
            )

        # Sử dụng Semantic Document Grader để hiệu chỉnh điểm và thẩm định chủ đề pháp lý
        grading_res: RetrievalGradingResult = self.grader.grade_documents(query, chunks)
        verdict = grading_res.overall_verdict
        overall_conf = grading_res.overall_confidence
        correct_count = grading_res.correct_count

        if verdict == GradeVerdict.CORRECT and correct_count >= 1:
            return PostRetrievalEvaluation(
                confidence_level=ConfidenceLevel.HIGH,
                overall_score=round(overall_conf, 3),
                num_chunks=len(chunks),
                num_relevant=correct_count,
                recommended_action=EscalationTarget.NONE,
                reason=f"Độ tin cậy CAO: {correct_count}/{len(chunks)} chunks khớp đúng chủ đề pháp luật (Điểm: {overall_conf:.3f}).",
                grading_result=grading_res.model_dump(),
            )

        elif verdict == GradeVerdict.AMBIGUOUS:
            # Nếu câu hỏi có nhiều vế điều kiện mà kết quả lơ lửng -> nâng cấp sang DECOMPOSE
            target = EscalationTarget.ESCALATE_TO_DECOMPOSE if is_multi_hop_query else EscalationTarget.ESCALATE_TO_CRAG
            return PostRetrievalEvaluation(
                confidence_level=ConfidenceLevel.AMBIGUOUS,
                overall_score=round(overall_conf, 3),
                num_chunks=len(chunks),
                num_relevant=correct_count,
                recommended_action=target,
                reason=f"Độ tin cậy KHÔNG RÕ RÀNG (AMBIGUOUS - Điểm: {overall_conf:.3f}). Cần nâng cấp sang {target.value} để tinh lọc dải tri thức.",
                grading_result=grading_res.model_dump(),
            )

        else:  # GradeVerdict.INCORRECT
            target = EscalationTarget.ESCALATE_TO_DECOMPOSE if is_multi_hop_query else EscalationTarget.ESCALATE_TO_CRAG
            return PostRetrievalEvaluation(
                confidence_level=ConfidenceLevel.LOW,
                overall_score=round(overall_conf, 3),
                num_chunks=len(chunks),
                num_relevant=correct_count,
                recommended_action=target,
                reason=f"Độ tin cậy THẤP / LẠC ĐỀ (INCORRECT - Điểm: {overall_conf:.3f}). Toàn bộ chunks không khớp điều luật, tự động nâng cấp sang {target.value}.",
                grading_result=grading_res.model_dump(),
            )

    def evaluate_subquery(
        self,
        sub_query_text: str,
        sub_chunks: List[RetrievedChunk],
    ) -> PostRetrievalEvaluation:
        """
        Đánh giá chuyên biệt cho từng truy vấn con (Sub-query) trong nhánh DECOMPOSE_AGENTIC.
        Nếu sub-query bị thiếu tài liệu hoặc lạc đề, đề xuất kích hoạt Web Search Fallback ngay lập tức.
        """
        if not sub_chunks or len(sub_chunks) == 0:
            return PostRetrievalEvaluation(
                confidence_level=ConfidenceLevel.EMPTY,
                overall_score=0.0,
                num_chunks=0,
                num_relevant=0,
                recommended_action=EscalationTarget.WEB_SEARCH_SUBQUERY,
                reason=f"Sub-query '{sub_query_text}' không tìm thấy điều luật nội bộ, kích hoạt Web Search.",
            )

        grading_res = self.grader.grade_documents(sub_query_text, sub_chunks)
        if grading_res.overall_verdict == GradeVerdict.INCORRECT:
            return PostRetrievalEvaluation(
                confidence_level=ConfidenceLevel.LOW,
                overall_score=round(grading_res.overall_confidence, 3),
                num_chunks=len(sub_chunks),
                num_relevant=grading_res.correct_count,
                recommended_action=EscalationTarget.WEB_SEARCH_SUBQUERY,
                reason=f"Sub-query '{sub_query_text}' có chunks lạc đề (Điểm: {grading_res.overall_confidence:.3f}), kích hoạt Web Search bổ trợ.",
                grading_result=grading_res.model_dump(),
            )

        return PostRetrievalEvaluation(
            confidence_level=ConfidenceLevel.HIGH if grading_res.overall_verdict == GradeVerdict.CORRECT else ConfidenceLevel.AMBIGUOUS,
            overall_score=round(grading_res.overall_confidence, 3),
            num_chunks=len(sub_chunks),
            num_relevant=grading_res.correct_count,
            recommended_action=EscalationTarget.NONE,
            reason="Sub-query có tài liệu nội bộ phù hợp.",
            grading_result=grading_res.model_dump(),
        )
