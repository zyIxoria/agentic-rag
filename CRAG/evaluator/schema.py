"""schema.py - Schema dữ liệu cho Retrieval Evaluator (Document Grader) trong CRAG."""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class GradeVerdict(str, Enum):
    """Trạng thái đánh giá mức độ liên quan của một đoạn tài liệu."""
    CORRECT = "CORRECT"        # Đoạn tài liệu có liên quan chặt chẽ, trực tiếp giải đáp câu hỏi
    INCORRECT = "INCORRECT"    # Đoạn tài liệu hoàn toàn lạc đề, không chứa thông tin cần thiết
    AMBIGUOUS = "AMBIGUOUS"    # Đoạn tài liệu chỉ liên quan gián tiếp, chứa một phần từ khóa nhưng chưa đủ chắc chắn


class ActionTrigger(str, Enum):
    """Hành động điều hướng tiếp theo của chuỗi Corrective RAG."""
    REFINE = "REFINE"                  # Tài liệu nội bộ tin cậy -> Tinh chỉnh (Decompose, Strip, Filter)
    WEB_SEARCH = "WEB_SEARCH"          # Toàn bộ tài liệu lạc đề -> Kích hoạt tìm kiếm bổ trợ ngoài web
    COMBINE_SEARCH = "COMBINE_SEARCH"  # Tài liệu mơ hồ -> Kết hợp cả tinh chỉnh nội bộ lẫn tìm kiếm ngoài
    REFUSE = "REFUSE"                  # Câu hỏi ngoài phạm vi hoặc thiếu chứng cứ nghiêm trọng -> Từ chối an toàn


class DocumentGrade(BaseModel):
    """Kết quả chấm điểm chi tiết cho một đoạn chunk thu hồi."""
    model_config = ConfigDict(extra="ignore")

    chunk_id: str = Field(..., description="ID định danh duy nhất của chunk")
    document_id: str = Field(default="", description="Mã văn bản pháp lý (VD: BLLD_2019)")
    article_number: Optional[str] = Field(default=None, description="Số hiệu Điều luật")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Điểm số mức độ phù hợp [0.0, 1.0]")
    verdict: GradeVerdict = Field(..., description="Kết luận phân loại: CORRECT, INCORRECT, AMBIGUOUS")
    reasoning: str = Field(default="", description="Lý giải ngắn gọn căn cứ chấm điểm")
    key_matches: List[str] = Field(default_factory=list, description="Các từ khóa/thực thể pháp lý khớp giữa query và chunk")


class RetrievalGradingResult(BaseModel):
    """Kết quả đánh giá tổng thể cho toàn bộ tập Top-K chunks thu hồi."""
    model_config = ConfigDict(extra="ignore")

    query: str = Field(..., description="Câu hỏi người dùng")
    individual_grades: List[DocumentGrade] = Field(default_factory=list, description="Chi tiết điểm của từng chunk")
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Độ tin cậy tổng thể của tập tài liệu thu hồi")
    overall_verdict: GradeVerdict = Field(..., description="Kết luận chung: CORRECT, INCORRECT, AMBIGUOUS")
    recommended_action: ActionTrigger = Field(..., description="Hành động đề xuất: REFINE, WEB_SEARCH, COMBINE_SEARCH, REFUSE")
    correct_count: int = Field(default=0, description="Số chunk đạt CORRECT")
    ambiguous_count: int = Field(default=0, description="Số chunk đạt AMBIGUOUS")
    incorrect_count: int = Field(default=0, description="Số chunk bị INCORRECT")
    latency_ms: float = Field(default=0.0, description="Thời gian thực thi của Grader (ms)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata bổ sung cho telemetry")

    @property
    def action(self) -> ActionTrigger:
        """Alias cho recommended_action."""
        return self.recommended_action
