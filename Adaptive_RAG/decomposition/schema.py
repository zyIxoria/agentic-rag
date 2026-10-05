"""
Adaptive RAG Query Decomposition Schemas.
Định nghĩa cấu trúc dữ liệu toàn diện cho Kế hoạch phân rã câu hỏi (Sub-query Decomposition & Execution Plan),
quan hệ phụ thuộc (DAG Dependencies), kiểm định (Validation), và nhật ký vết (Tracing).
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class DecompositionType(str, Enum):
    """Phân loại dạng thức phân rã câu hỏi theo taxonomy học thuật."""
    MULTI_ISSUE = "MULTI_ISSUE"                    # Đa vấn đề pháp lý độc lập (quyền lợi, nghĩa vụ)
    MULTI_CONDITION = "MULTI_CONDITION"            # Đa điều kiện ràng buộc tình huống (nếu... thì...)
    CROSS_REFERENCE = "CROSS_REFERENCE"            # Viện dẫn chéo giữa các Điều luật/Văn bản
    MULTI_DOCUMENT = "MULTI_DOCUMENT"              # Đa văn bản quy phạm pháp luật (Luật + NĐ/TT)
    CONDITIONAL_TEMPORAL = "CONDITIONAL_TEMPORAL"  # Điều kiện thời gian, mốc thời kỳ quá độ
    NONE = "NONE"                                  # Câu hỏi đơn giản, không phân rã


class ExecutionStrategy(str, Enum):
    """Chiến lược thực thi các truy vấn con."""
    PARALLEL = "PARALLEL"        # Thực thi song song độc lập (các sub-queries không phụ thuộc lẫn nhau)
    SEQUENTIAL = "SEQUENTIAL"    # Thực thi tuần tự (kết quả sub-query trước làm đầu vào cho sub-query sau)
    HYBRID = "HYBRID"            # Kết hợp song song các truy vấn độc lập và tuần tự cho truy vấn phụ thuộc


class SubQuery(BaseModel):
    """Một truy vấn con nguyên tử sau phân rã."""
    model_config = ConfigDict(extra="ignore")

    sub_id: str = Field(..., description="ID định danh truy vấn con (VD: sub_1, sub_2)")
    text: str = Field(..., description="Nội dung câu hỏi con đã được bảo toàn ngữ cảnh hoàn chỉnh")
    intent: Optional[str] = Field(default=None, description="Ý định pháp lý chính của truy vấn con")
    target_entity: Optional[str] = Field(default=None, description="Thực thể pháp lý nhắm tới (VD: Điều 125, NĐ 145/2020)")
    entities: List[str] = Field(default_factory=list, description="Danh sách các thực thể pháp lý liên quan")
    constraints: List[str] = Field(default_factory=list, description="Các ràng buộc/điều kiện (VD: ban đêm, mang thai)")
    dependency_ids: List[str] = Field(default_factory=list, description="Danh sách sub_id mà truy vấn này phụ thuộc")
    execution_order: int = Field(default=1, description="Thứ tự thực thi ưu tiên")
    sub_type: Optional[str] = Field(default=None, description="Loại truy vấn con (VD: precondition, calculation, rule)")

    @property
    def id(self) -> str:
        """Alias cho sub_id theo chuẩn giao diện."""
        return self.sub_id

    @property
    def dependencies(self) -> List[str]:
        """Alias cho dependency_ids."""
        return self.dependency_ids


class ValidationResult(BaseModel):
    """Kết quả kiểm định chất lượng các câu hỏi con sau phân rã."""
    model_config = ConfigDict(extra="ignore")

    is_valid: bool = Field(..., description="True nếu vượt qua toàn bộ các bài kiểm tra chất lượng")
    coverage_score: float = Field(default=1.0, description="Tỷ lệ bao phủ ý định câu hỏi gốc (0.0 đến 1.0)")
    context_preserved: bool = Field(default=True, description="True nếu không bị mất chủ thể, điều kiện hay mốc thời gian")
    has_redundancy: bool = Field(default=False, description="True nếu có các câu hỏi con bị trùng lặp nội dung")
    is_atomic: bool = Field(default=True, description="True nếu mỗi câu hỏi con đủ nhỏ gọn, độc lập")
    retrieval_suitable: bool = Field(default=True, description="True nếu phù hợp làm đầu vào cho Dense/CRAG Retriever")
    issues: List[str] = Field(default_factory=list, description="Danh sách các cảnh báo hoặc lỗi phát hiện được")


class DecompositionTrace(BaseModel):
    """Nhật ký dấu vết quá trình phân rã câu hỏi phục vụ giải trình học thuật."""
    model_config = ConfigDict(extra="ignore")

    original_query: str = Field(..., description="Câu hỏi gốc")
    detected_complexity: str = Field(default="UNKNOWN", description="Mức độ phức tạp phát hiện từ Classifier")
    taxonomy_types: List[str] = Field(default_factory=list, description="Các dạng phân rã được nhận diện")
    initial_sub_queries: List[str] = Field(default_factory=list, description="Danh sách câu hỏi con sinh ra ban đầu")
    validation_result: Optional[ValidationResult] = Field(default=None, description="Kết quả kiểm định lần đầu")
    repair_attempted: bool = Field(default=False, description="True nếu đã kích hoạt cơ chế sửa chữa (Repair Loop)")
    repair_reason: Optional[str] = Field(default=None, description="Lý do kích hoạt sửa chữa")
    final_sub_queries: List[str] = Field(default_factory=list, description="Danh sách câu hỏi con cuối cùng")
    latency_ms: float = Field(default=0.0, description="Độ trễ phân rã tính bằng mili-giây")


class DecompositionPlan(BaseModel):
    """
    Kế hoạch phân rã và điều phối truy vấn con hoàn chỉnh.
    Đồng thời đóng vai trò QueryDecompositionResult theo đặc tả của Module 11.
    """
    model_config = ConfigDict(extra="ignore")

    original_query: str = Field(..., description="Câu hỏi gốc ban đầu của người dùng")
    decomposition_required: bool = Field(default=True, description="True nếu câu hỏi thực sự cần phân rã")
    decomposition_type: List[DecompositionType] = Field(default_factory=list, description="Dạng thức phân rã áp dụng")
    sub_queries: List[SubQuery] = Field(default_factory=list, description="Danh sách các truy vấn con nguyên tử")
    strategy: ExecutionStrategy = Field(default=ExecutionStrategy.PARALLEL, description="Chiến lược thực thi (PARALLEL/SEQUENTIAL/HYBRID)")
    reasoning_dependencies: List[Dict[str, Any]] = Field(default_factory=list, description="Đồ thị quan hệ phụ thuộc suy luận giữa các câu hỏi con")
    synthesis_instruction: str = Field(default="", description="Chỉ dẫn tổng hợp câu trả lời cuối cùng từ các kết quả thành phần")
    validation: Optional[ValidationResult] = Field(default=None, description="Chi tiết kết quả kiểm định câu hỏi con")
    repair_applied: bool = Field(default=False, description="True nếu đã trải qua bước tự động sửa chữa")
    trace: Optional[DecompositionTrace] = Field(default=None, description="Nhật ký truy vết quá trình phân rã")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata bổ sung cho điều phối Agentic")
    latency_ms: float = Field(default=0.0, description="Thời gian thực thi phân rã (mili-giây)")


# Alias chuẩn theo đặc tả Module 11
QueryDecompositionResult = DecompositionPlan
