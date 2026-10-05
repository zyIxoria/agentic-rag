"""
Adaptive RAG Classifier Schemas.
Định nghĩa cấu trúc dữ liệu cho bộ phân loại độ phức tạp và ý định câu hỏi (Query Complexity & Intent Classifier).
Phục vụ Module 0 - Query Complexity Classifier và Adaptive Router.
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# CHUẨN MỨC MỚI: 3-CLASS COMPLEXITY TAXONOMY THEO ĐẶC TẢ MODULE 0
# =============================================================================

class ComplexityClass(str, Enum):
    """3 mức độ phức tạp pháp lý của câu hỏi theo đặc tả Module 0."""
    SIMPLE = "SIMPLE"          # 1 vấn đề pháp lý, 1 Điều/Khoản, direct retrieval
    MODERATE = "MODERATE"      # Nhiều điều kiện/thủ tục, cần CRAG verification, chưa cần decomposition
    COMPLEX = "COMPLEX"        # Đa văn bản, đa điều khoản, viện dẫn chéo, tính toán, cần decomposition


class RoutingStrategy(str, Enum):
    """Chiến lược điều phối tương ứng cho từng mức độ phức tạp."""
    DIRECT_RAG = "DIRECT_RAG"                    # Dùng Direct / Traditional RAG
    CRAG = "CRAG"                                # Dùng Corrective RAG (Retrieve -> Grader -> Rewrite)
    DECOMPOSITION_CRAG = "DECOMPOSITION_CRAG"    # Dùng Query Decomposition + CRAG


class QueryComplexityFeatures(BaseModel):
    """Tập đặc trưng phân tích độ phức tạp pháp lý (Legal Complexity Features)."""
    model_config = ConfigDict(extra="ignore")

    number_of_legal_issues: int = Field(default=1, description="Số lượng vấn đề/chủ đề pháp lý xuất hiện")
    multi_condition: bool = Field(default=False, description="Chứa nhiều vế điều kiện (nếu... thì, vừa... vừa, đồng thời)")
    multi_document: bool = Field(default=False, description="Đòi hỏi đối chiếu hoặc viện dẫn từ >= 2 văn bản quy phạm")
    cross_reference: bool = Field(default=False, description="Chứa viện dẫn chéo giữa các điều khoản khác nhau")
    temporal_condition: bool = Field(default=False, description="Chứa ràng buộc thời gian (thử việc, ban đêm, ngày lễ, số ngày)")
    subject_count: int = Field(default=1, description="Số lượng chủ thể pháp lý liên quan")
    required_reasoning_steps: int = Field(default=1, description="Số bước suy luận pháp lý ước tính")
    calculation_required: bool = Field(default=False, description="Đòi hỏi tính toán số học (tiền lương, trợ cấp, % làm thêm)")
    procedural_required: bool = Field(default=False, description="Đòi hỏi trình tự, thủ tục, hồ sơ nhiều bước")
    ambiguity: bool = Field(default=False, description="Câu hỏi mơ hồ, dùng từ đời thường hoặc thiếu dữ kiện")
    decomposition_required: bool = Field(default=False, description="Cần phân rã thành các câu hỏi con độc lập")

    detected_articles: List[str] = Field(default_factory=list, description="Danh sách các số điều luật phát hiện được")
    detected_documents: List[str] = Field(default_factory=list, description="Danh sách tên văn bản pháp luật phát hiện được")
    detected_subjects: List[str] = Field(default_factory=list, description="Danh sách các chủ thể pháp lý phát hiện được")
    is_out_of_scope: bool = Field(default=False, description="Câu hỏi nằm ngoài phạm vi pháp luật lao động")
    is_greeting: bool = Field(default=False, description="Câu hỏi mang tính chào hỏi/xã giao")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class QueryComplexityResult(BaseModel):
    """Kết quả phân loại độ phức tạp câu hỏi chuẩn Module 0 phục vụ Adaptive Router."""
    model_config = ConfigDict(extra="ignore")

    query: str = Field(..., description="Câu hỏi nguyên bản của người dùng")
    complexity: ComplexityClass = Field(..., description="Mức độ phức tạp: SIMPLE | MODERATE | COMPLEX")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Độ tin cậy của phân loại [0.0, 1.0]")
    reasons: List[str] = Field(default_factory=list, description="Danh sách các lý do giải thích căn cứ phân loại")
    features: Dict[str, Any] = Field(default_factory=dict, description="Bảng các đặc trưng phân tích được")
    recommended_strategy: RoutingStrategy = Field(..., description="Chiến lược điều phối khuyến nghị")
    latency_ms: float = Field(default=0.0, description="Thời gian thực thi phân loại (ms)")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "complexity": self.complexity.value,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "features": self.features,
            "recommended_strategy": self.recommended_strategy.value,
            "latency_ms": self.latency_ms,
        }


# =============================================================================
# LEGACY SCHEMAS PHỤC VỤ TƯƠNG THÍCH NGƯỢC VỚI CÁC TEST HIỆN CÓ
# =============================================================================

class QueryIntent(str, Enum):
    """Ý định chính của câu hỏi người dùng."""
    GREETING_CHITCHAT = "GREETING_CHITCHAT"        # Chào hỏi, xã giao, cảm ơn
    OUT_OF_SCOPE = "OUT_OF_SCOPE"                  # Ngoài phạm vi pháp luật lao động Việt Nam
    LEGAL_DIRECT_DEFINITION = "LEGAL_DIRECT_DEF"    # Tra cứu khái niệm/điều khoản trực tiếp
    LEGAL_CONDITIONAL = "LEGAL_CONDITIONAL"        # Câu hỏi tình huống có điều kiện
    LEGAL_MULTI_DOCUMENT = "LEGAL_MULTI_DOC"       # Câu hỏi liên quan nhiều văn bản quy phạm
    LEGAL_PROCEDURAL = "LEGAL_PROCEDURAL"          # Câu hỏi về quy trình, thủ tục các bước
    LEGAL_INSUFFICIENT = "LEGAL_INSUFFICIENT"      # Câu hỏi thiếu dữ kiện hoặc giả định mâu thuẫn


class ComplexityLevel(str, Enum):
    """Mức độ phức tạp của câu hỏi (Legacy 4-level)."""
    DIRECT = "DIRECT"                              # Không cần truy xuất (chào hỏi / ngoài phạm vi)
    SIMPLE_SINGLE_HOP = "SIMPLE_SINGLE_HOP"        # Đơn giản, 1 lần truy xuất đơn lẻ là đủ
    MODERATE_CORRECTIVE = "MODERATE_CORRECTIVE"    # Trung bình, cần lọc nhiễu hoặc có thể trôi ngữ cảnh
    COMPLEX_MULTI_HOP = "COMPLEX_MULTI_HOP"        # Phức tạp, cần bẻ nhỏ thành sub-queries


class RoutingDecision(str, Enum):
    """Quyết định điều phối luồng xử lý tối ưu (Legacy)."""
    DIRECT_ANSWER = "DIRECT_ANSWER"                # Phản hồi tức thì không tra cứu
    DIRECT_REFUSAL = "DIRECT_REFUSAL"              # Từ chối an toàn ngay tại cửa ngõ
    TRADITIONAL_RAG = "TRADITIONAL_RAG"            # Điều phối về Traditional RAG Baseline
    CORRECTIVE_RAG = "CORRECTIVE_RAG"              # Điều phối về Corrective RAG (CRAG)
    DECOMPOSE_AGENTIC = "DECOMPOSE_AGENTIC"        # Điều phối về Agentic Sub-query Planner


class ClassificationResult(BaseModel):
    """Kết quả phân loại câu hỏi toàn diện (Legacy)."""
    model_config = ConfigDict(extra="ignore")

    query: str = Field(..., description="Câu hỏi người dùng")
    intent: QueryIntent = Field(..., description="Ý định câu hỏi")
    complexity: ComplexityLevel = Field(..., description="Mức độ phức tạp")
    suggested_route: RoutingDecision = Field(..., description="Quyết định định tuyến thích ứng")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Độ tin cậy của bộ phân loại [0.0, 1.0]")
    reasoning: str = Field(default="", description="Lý giải căn cứ phân loại")
    detected_articles: List[str] = Field(default_factory=list, description="Các số điều luật phát hiện được")
    detected_documents: List[str] = Field(default_factory=list, description="Các văn bản luật phát hiện được")
    detected_conditions: List[str] = Field(default_factory=list, description="Các vế điều kiện phức hợp")
    latency_ms: float = Field(default=0.0, description="Thời gian thực thi phân loại (ms)")
