"""schemas.py - Định nghĩa cấu trúc dữ liệu cho Corrective RAG (CRAG).

Bao gồm:
- EvaluationStatus: SUFFICIENT | PARTIAL | INSUFFICIENT
- RetrievalEvaluation: Kết quả đánh giá mức độ đủ bằng chứng của các chunk thu hồi
- CRAGResponse: Phản hồi đầu ra toàn diện của pipeline kèm trace thực thi
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

from RAG.retriever.schema import RetrievedChunk
from RAG.citation.schema import LegalCitation
from RAG.schemas.pipeline_schema import RAGResponse


class EvaluationStatus(str, Enum):
    """Trạng thái đánh giá mức độ đầy đủ của ngữ cảnh thu hồi."""
    SUFFICIENT = "SUFFICIENT"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"


class RetrievalEvaluation(BaseModel):
    """Schema đánh giá chất lượng tài liệu thu hồi bởi Retrieval Evaluator."""

    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    status: EvaluationStatus = Field(
        ...,
        description="Mức độ đầy đủ căn cứ: SUFFICIENT | PARTIAL | INSUFFICIENT"
    )
    confidence: float = Field(
        ...,
        description="Độ tin cậy của đánh giá, giá trị bắt buộc trong đoạn [0.0, 1.0]"
    )
    relevant_chunk_ids: List[str] = Field(
        default_factory=list,
        description="Danh sách ID các chunk chứa bằng chứng trả lời câu hỏi"
    )
    irrelevant_chunk_ids: List[str] = Field(
        default_factory=list,
        description="Danh sách ID các chunk gây nhiễu hoặc không chứa bằng chứng"
    )
    reason: str = Field(
        ...,
        description="Giải thích ngắn gọn lý do tại sao retrieval đủ, thiếu hoặc không liên quan"
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence_range(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError(f"Confidence phải nằm trong đoạn [0.0, 1.0], nhận được: {v}")
        return round(float(v), 4)

    @field_validator("status", mode="before")
    @classmethod
    def validate_status_enum(cls, v: Any) -> EvaluationStatus:
        if isinstance(v, EvaluationStatus):
            return v
        if isinstance(v, str):
            v_upper = v.strip().upper()
            try:
                return EvaluationStatus(v_upper)
            except ValueError:
                raise ValueError(f"Trạng thái đánh giá không hợp lệ: '{v}'. Chấp nhận: {[e.value for e in EvaluationStatus]}")
        raise ValueError(f"Kiểu dữ liệu trạng thái không hợp lệ: {type(v)}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "confidence": self.confidence,
            "relevant_chunk_ids": self.relevant_chunk_ids,
            "irrelevant_chunk_ids": self.irrelevant_chunk_ids,
            "reason": self.reason,
        }


class CRAGResponse(RAGResponse):
    """Cấu trúc dữ liệu phản hồi cuối cùng từ Corrective RAG Pipeline, bảo toàn tương thích với RAGResponse."""

    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    original_query: str = Field(
        ...,
        description="Câu hỏi/truy vấn ban đầu của người dùng"
    )
    initial_retrieval: List[RetrievedChunk] = Field(
        default_factory=list,
        description="Danh sách các chunk thu hồi lần 1"
    )
    initial_evaluation: RetrievalEvaluation = Field(
        ...,
        description="Kết quả đánh giá retrieval lần 1"
    )
    corrective_triggered: bool = Field(
        default=False,
        description="True nếu hệ thống kích hoạt chu trình hiệu chỉnh truy vấn và thu hồi lại"
    )
    rewritten_query: Optional[str] = Field(
        default=None,
        description="Truy vấn được viết lại bởi Query Rewriter (None nếu không kích hoạt)"
    )
    corrective_retrieval: List[RetrievedChunk] = Field(
        default_factory=list,
        description="Danh sách các chunk thu hồi lần 2 sau khi viết lại truy vấn"
    )
    final_evaluation: RetrievalEvaluation = Field(
        ...,
        description="Kết quả đánh giá retrieval cuối cùng trước khi đưa vào Generator"
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        le=1,
        description="Số lần thực hiện corrective retrieval (tối đa 1)"
    )
    latency_ms: float = Field(
        default=0.0,
        description="Tổng thời gian thực thi của CRAG pipeline tính bằng mili-giây (ms)"
    )
    eval_latency: float = Field(
        default=0.0,
        description="Thời gian đánh giá retrieval (ms)"
    )
    rewrite_latency: float = Field(
        default=0.0,
        description="Thời gian viết lại truy vấn (ms)"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Xuất đầy đủ dữ liệu phản hồi và execution trace phục vụ phân tích thực nghiệm."""
        base_dict = super().to_dict()
        base_dict.update({
            "original_query": self.original_query,
            "initial_retrieval": [c.to_dict() for c in self.initial_retrieval],
            "initial_evaluation": self.initial_evaluation.to_dict(),
            "corrective_triggered": self.corrective_triggered,
            "rewritten_query": self.rewritten_query,
            "corrective_retrieval": [c.to_dict() for c in self.corrective_retrieval],
            "final_evaluation": self.final_evaluation.to_dict(),
            "retry_count": self.retry_count,
            "latency_ms": self.latency_ms or self.latency,
            "eval_latency": self.eval_latency,
            "rewrite_latency": self.rewrite_latency,
        })
        return base_dict
