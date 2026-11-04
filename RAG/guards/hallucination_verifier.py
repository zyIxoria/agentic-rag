"""
Real-time Hallucination Verifier and Self-Reflection Faithfulness Gate.
Kiểm chứng tính trung thành theo thời gian thực (Claim-level Faithfulness & Entailment Verification)
trước khi gửi câu trả lời về cho người dùng.
"""

from __future__ import annotations
import re
import logging
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


class ClaimStatus(str, Enum):
    """Trạng thái kiểm chứng của từng mệnh đề (Atomic Claim)."""
    ENTAILED = "ENTAILED"          # Mệnh đề được chứng minh/suy diễn trực tiếp từ ngữ cảnh
    CONTRADICTED = "CONTRADICTED"  # Mệnh đề mâu thuẫn trực tiếp với điều luật trong ngữ cảnh
    UNSUPPORTED = "UNSUPPORTED"    # Mệnh đề không tìm thấy căn cứ hỗ trợ nào trong ngữ cảnh


class ClaimVerificationResult(BaseModel):
    """Kết quả kiểm chứng một mệnh đề độc lập."""
    model_config = ConfigDict(extra="ignore")

    claim_text: str
    status: ClaimStatus
    confidence: float = 1.0
    matched_snippet: Optional[str] = None
    reason: str = ""


class FaithfulnessVerificationReport(BaseModel):
    """Báo cáo kiểm chứng trung thực và phát hiện ảo giác toàn diện."""
    model_config = ConfigDict(extra="ignore")

    passed: bool
    faithfulness_score: float = Field(..., ge=0.0, le=1.0)
    total_claims: int = 0
    entailed_count: int = 0
    unsupported_count: int = 0
    contradicted_count: int = 0
    hallucination_detected: bool = False
    claims: List[ClaimVerificationResult] = Field(default_factory=list)
    action_taken: str = "ALLOW"
    filtered_answer: Optional[str] = None
    reason: str = ""


class RealTimeHallucinationVerifier:
    """
    Bộ kiểm chứng ảo giác thời gian thực (Self-Reflection Faithfulness Gate):
    1. Tách câu trả lời thành danh sách các mệnh đề/khẳng định sự thật (Claim Decomposition).
    2. Đối chiếu từng mệnh đề với toàn bộ ngữ cảnh pháp lý thu hồi được (Context Entailment Check).
    3. Phát hiện số hiệu điều luật bịa đặt, con số định lượng sai lệch, và các mệnh đề không có căn cứ.
    4. Kích hoạt hành động tự suy ngẫm (Self-Reflection): Cho phép, Cắt tỉa (Prune), hoặc Cưỡng chế từ chối (Block).
    """

    def __init__(
        self,
        faithfulness_threshold: float = 0.65,
        min_overlap_ratio: float = 0.40,
    ):
        self.faithfulness_threshold = faithfulness_threshold
        self.min_overlap_ratio = min_overlap_ratio

    def extract_claims(self, text: str) -> List[str]:
        """
        Phân rã văn bản câu trả lời thành các mệnh đề/câu mang nội dung khẳng định pháp lý.
        Loại bỏ câu chào hỏi, chuyển tiếp vô nghĩa.
        """
        # Tách theo dấu chấm, chấm phẩy, xuống dòng
        raw_sentences = re.split(r"(?<=[.!?\n])\s+", text)
        claims: List[str] = []

        # Các cụm từ chào hỏi hoặc chuyển ý cần bỏ qua
        ignore_patterns = [
            r"^xin chào",
            r"^cảm ơn bạn",
            r"^tôi có thể giúp",
            r"^dưới đây là",
            r"^sau đây là",
            r"^chúc bạn",
            r"^kết luận:",
        ]

        for s in raw_sentences:
            s_clean = s.strip()
            # Bỏ qua câu quá ngắn hoặc mang tính thủ tục xã giao
            if len(s_clean) < 15:
                continue
            if any(re.search(pat, s_clean.lower()) for pat in ignore_patterns):
                continue
            claims.append(s_clean)

        return claims

    def verify(
        self,
        answer: str,
        context: str,
    ) -> FaithfulnessVerificationReport:
        """
        Thực hiện kiểm chứng tính trung thành toàn diện giữa answer và context.
        """
        if not answer or not answer.strip():
            return FaithfulnessVerificationReport(
                passed=False,
                faithfulness_score=0.0,
                reason="Câu trả lời rỗng.",
                action_taken="BLOCK_REFUSAL",
            )

        if not context or not context.strip():
            return FaithfulnessVerificationReport(
                passed=False,
                faithfulness_score=0.0,
                hallucination_detected=True,
                reason="Không có ngữ cảnh pháp lý làm căn cứ kiểm chứng.",
                action_taken="BLOCK_REFUSAL",
            )

        claims = self.extract_claims(answer)
        if not claims:
            # Không có mệnh đề khẳng định cụ thể nào
            return FaithfulnessVerificationReport(
                passed=True,
                faithfulness_score=1.0,
                total_claims=0,
                action_taken="ALLOW",
                reason="Không có mệnh đề sự thật cần kiểm chứng.",
            )

        context_lower = context.lower()
        verified_claims: List[ClaimVerificationResult] = []
        entailed_count = 0
        unsupported_count = 0
        contradicted_count = 0

        # Trích xuất danh sách tất cả các số hiệu Điều luật có trong Context
        context_articles = set(re.findall(r"điều\s+(\d+[a-zA-Z]*)", context_lower))

        for claim in claims:
            claim_lower = claim.lower()

            # 1. Kiểm tra ảo giác số hiệu Điều luật (Article Hallucination Check)
            claim_articles = set(re.findall(r"điều\s+(\d+[a-zA-Z]*)", claim_lower))
            hallucinated_articles = claim_articles - context_articles

            if hallucinated_articles:
                # Bịa đặt số điều luật không hề có trong tài liệu
                contradicted_count += 1
                verified_claims.append(
                    ClaimVerificationResult(
                        claim_text=claim,
                        status=ClaimStatus.CONTRADICTED,
                        confidence=0.95,
                        reason=f"Viện dẫn số Điều không tồn tại trong tài liệu tham khảo: {', '.join(hallucinated_articles)}",
                    )
                )
                continue

            # 2. Kiểm tra độ trùng khớp thực thể và từ khóa ngữ nghĩa (Lexical-Semantic Entailment)
            words = [w for w in re.findall(r"\w+", claim_lower) if len(w) >= 3]
            if not words:
                entailed_count += 1
                verified_claims.append(
                    ClaimVerificationResult(claim_text=claim, status=ClaimStatus.ENTAILED, confidence=1.0)
                )
                continue

            matches = [w for w in words if w in context_lower]
            overlap_ratio = len(matches) / len(words)

            # Kiểm tra cụm số/thực thể định lượng
            numbers_in_claim = re.findall(r"\b\d+[\d\.,]*\b", claim_lower)
            numbers_match = all(num in context_lower for num in numbers_in_claim) if numbers_in_claim else True

            if overlap_ratio >= self.min_overlap_ratio and numbers_match:
                entailed_count += 1
                verified_claims.append(
                    ClaimVerificationResult(
                        claim_text=claim,
                        status=ClaimStatus.ENTAILED,
                        confidence=round(overlap_ratio, 3),
                        reason=f"Mệnh đề có tỷ lệ trùng khớp ngữ nghĩa {overlap_ratio:.1%} với ngữ cảnh.",
                    )
                )
            else:
                unsupported_count += 1
                verified_claims.append(
                    ClaimVerificationResult(
                        claim_text=claim,
                        status=ClaimStatus.UNSUPPORTED,
                        confidence=round(1.0 - overlap_ratio, 3),
                        reason=f"Không tìm thấy đủ căn cứ chứng minh trong ngữ cảnh (trùng khớp {overlap_ratio:.1%}).",
                    )
                )

        total = len(claims)
        faithfulness = entailed_count / total if total > 0 else 1.0
        hallucination_detected = (contradicted_count > 0) or (faithfulness < self.faithfulness_threshold)

        # Quyết định hành động Self-Reflection
        if contradicted_count > 0 or faithfulness < 0.40:
            action = "BLOCK_REFUSAL"
            passed = False
            reason = f"Phát hiện ảo giác nghiêm trọng ({contradicted_count} điều luật bịa đặt, faithfulness={faithfulness:.2f}). Cưỡng chế từ chối."
        elif hallucination_detected:
            action = "APPEND_DISCLAIMER"
            passed = True  # Cho qua nhưng cảnh báo
            reason = f"Độ trung thực trung bình (faithfulness={faithfulness:.2f}). Đính kèm khuyến cáo."
        else:
            action = "ALLOW"
            passed = True
            reason = f"Kiểm chứng trung thực đạt chuẩn (faithfulness={faithfulness:.2f})."

        # Lọc sạch các mệnh đề unsupported nếu cần tạo cleaned_answer
        valid_sentences = [
            vc.claim_text for vc in verified_claims if vc.status == ClaimStatus.ENTAILED
        ]
        cleaned_answer = " ".join(valid_sentences) if valid_sentences else None

        return FaithfulnessVerificationReport(
            passed=passed,
            faithfulness_score=round(faithfulness, 4),
            total_claims=total,
            entailed_count=entailed_count,
            unsupported_count=unsupported_count,
            contradicted_count=contradicted_count,
            hallucination_detected=hallucination_detected,
            claims=verified_claims,
            action_taken=action,
            filtered_answer=cleaned_answer,
            reason=reason,
        )
