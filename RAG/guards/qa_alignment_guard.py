"""qa_alignment_guard.py - Tier 4: Post-Generation QA Alignment Guard.

Kiểm tra tính nhất quán, tính trung thực và trích dẫn sau khi mô hình sinh câu trả lời:
1. Atomic Claim Decomposition: Phân rã câu trả lời thành các nhận định pháp lý nguyên tử.
2. Kiểm chứng từng nhận định:
   - VERIFIED: Được hậu thuẫn trực tiếp từ context chunks.
   - CALCULATED_VALID: Số liệu tính toán hợp lệ bắt nguồn từ công thức luật định.
   - UNSUPPORTED_CLAIM: Nhận định suy diễn không có căn cứ hoặc sai số hiệu Điều luật.
3. Selective Claim Pruning: Cắt tỉa chọn lọc nhận định phụ sai lệch, giữ lại câu trả lời cốt lõi vững chắc.
4. Từ chối an toàn: Chỉ từ chối khi luận điểm nòng cốt bị sai hoặc không còn giải quyết được câu hỏi.
"""

from __future__ import annotations
import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field

from RAG.retriever.schema import RetrievedChunk

logger = logging.getLogger("RAG.guards.qa_alignment")


class AtomicClaim(BaseModel):
    """Một mệnh đề nhận định pháp lý nguyên tử trong câu trả lời."""

    text: str
    is_core_verdict: bool = False
    is_verified: bool = False
    is_calculated_valid: bool = False
    is_unsupported: bool = False
    evidence_source: Optional[str] = None


class QAAlignmentResult(BaseModel):
    """Kết quả kiểm chứng và căn chỉnh sau sinh từ Tier 4."""

    is_aligned: bool = True
    trigger_refusal: bool = False
    refusal_reason: Optional[str] = None
    pruned_answer: Optional[str] = None
    total_claims: int = 0
    verified_claims_count: int = 0
    unsupported_claims_count: int = 0
    claims_detail: List[AtomicClaim] = Field(default_factory=list)


class PostGenerationQAAlignmentGuard:
    """Chốt chặn kiểm chứng và căn chỉnh câu trả lời sau sinh (Tier 4 Guard)."""

    def __init__(self, reject_on_core_failure: bool = True):
        self.reject_on_core_failure = reject_on_core_failure

    def _split_into_claims(self, text: str) -> List[str]:
        """Tách câu trả lời thành các mệnh đề hoặc câu riêng biệt."""
        # Tách theo dấu chấm, chấm phẩy, xuống dòng hoặc gạch đầu dòng
        sentences = re.split(r"(?<=[.!?])\s+|\n+|(?:^|\n)\s*[-*•]\s*|\d+\.\s+", text)
        claims = [s.strip() for s in sentences if len(s.strip()) > 15]
        return claims

    def _is_calculated_valid(self, claim: str, context_text: str) -> bool:
        """Kiểm tra xem mệnh đề có chứa số liệu tính toán hợp lệ từ công thức luật định hay không."""
        # Nhận diện các công thức định lượng phổ biến trong luật lao động
        # Ví dụ: 150%, 200%, 300% lương làm thêm giờ; 30% lương làm đêm; trợ cấp thôi việc = 1/2 tháng lương
        calc_patterns = [
            r"\b(150%|200%|300%|390%)\b",
            r"\b(30%|20%|15%|8%|14%|1%)\b",
            r"\b(nửa\s+tháng|1/2\s+tháng|một\s+tháng|01\s+tháng)\s+lương\b",
            r"\b(30\s+ngày|45\s+ngày|120\s+ngày|03\s+ngày|05\s+ngày|14\s+ngày)\b",
            r"\b(12\s+ngày|14\s+ngày|16\s+ngày)\s+(phép|nghỉ\s+hằng\s+năm)\b",
        ]
        for pat in calc_patterns:
            if re.search(pat, claim, re.IGNORECASE):
                # Kiểm tra xem từ khóa tương ứng có xuất hiện trong context không
                words = re.findall(r"\b\w{3,}\b", claim.lower())
                overlap = sum(1 for w in words if w in context_text.lower())
                if overlap >= 3:
                    return True
        return False

    def evaluate_answer(
        self,
        query: str,
        draft_answer: str,
        context_chunks: List[RetrievedChunk],
    ) -> QAAlignmentResult:
        """Kiểm chứng câu trả lời dự thảo so với các đoạn trích context thu hồi."""
        if not draft_answer or not draft_answer.strip():
            return QAAlignmentResult(
                is_aligned=False,
                trigger_refusal=True,
                refusal_reason="Câu trả lời dự thảo rỗng.",
            )

        # Nếu draft_answer đã là câu từ chối chuẩn thì cho qua
        if any(kw in draft_answer.lower() for kw in [
            "không tìm thấy", "chưa đủ căn cứ", "không có căn cứ",
            "nằm ngoài phạm vi", "chưa hỗ trợ tra cứu"
        ]):
            return QAAlignmentResult(
                is_aligned=True,
                trigger_refusal=False,
                pruned_answer=draft_answer,
            )

        context_full = " ".join([c.content for c in context_chunks if c.content])
        claims_raw = self._split_into_claims(draft_answer)
        if not claims_raw:
            return QAAlignmentResult(is_aligned=True, pruned_answer=draft_answer)

        claim_objects: List[AtomicClaim] = []
        valid_sentences: List[str] = []

        for i, c_text in enumerate(claims_raw):
            c_lower = c_text.lower()
            is_core = (i == 0) or any(k in c_lower for k in [
                "căn cứ", "theo quy định", "không được", "có quyền", "được hưởng", "bị xử phạt"
            ])

            # Kiểm tra trích dẫn Điều luật có trong context hay không
            cited_articles = re.findall(r"\bđiều\s+(\d+)\b", c_lower)
            has_invalid_article = False
            if cited_articles:
                for art in cited_articles:
                    # Kiểm tra xem Điều art có xuất hiện trong context không
                    if not re.search(rf"\bđiều\s+{art}\b", context_full.lower()):
                        has_invalid_article = True
                        break

            if has_invalid_article:
                claim_objects.append(AtomicClaim(
                    text=c_text,
                    is_core_verdict=is_core,
                    is_unsupported=True,
                    evidence_source="CITED_ARTICLE_ABSENT_IN_CONTEXT"
                ))
                continue

            # Kiểm tra overlap từ vựng quan trọng với context
            words = [w for w in re.findall(r"\b\w{3,}\b", c_lower) if w not in [
                "người", "theo", "được", "trong", "những", "trường", "hợp", "pháp", "luật", "quy", "định"
            ]]
            overlap_count = sum(1 for w in words if w in context_full.lower())
            overlap_ratio = overlap_count / max(1, len(words))

            is_calc = self._is_calculated_valid(c_text, context_full)

            if overlap_ratio >= 0.35 or is_calc:
                claim_objects.append(AtomicClaim(
                    text=c_text,
                    is_core_verdict=is_core,
                    is_verified=True,
                    is_calculated_valid=is_calc,
                    is_unsupported=False,
                    evidence_source="CONTEXT_GROUNDED"
                ))
                valid_sentences.append(c_text)
            else:
                claim_objects.append(AtomicClaim(
                    text=c_text,
                    is_core_verdict=is_core,
                    is_unsupported=True,
                    evidence_source="LOW_CONTEXT_OVERLAP"
                ))

        verified_count = sum(1 for c in claim_objects if c.is_verified)
        unsupported_count = sum(1 for c in claim_objects if c.is_unsupported)

        # Kiểm tra xem có nhận định cốt lõi nào bị unsupported không
        core_claims = [c for c in claim_objects if c.is_core_verdict]
        core_failed = any(c.is_unsupported for c in core_claims) if core_claims else False

        if core_failed and self.reject_on_core_failure and (verified_count == 0):
            logger.info("Tier 4 QA Guard: Core claim unsupported -> Triggers full refusal")
            return QAAlignmentResult(
                is_aligned=False,
                trigger_refusal=True,
                refusal_reason="Luận điểm cốt lõi trong câu trả lời không có căn cứ từ văn bản thu hồi.",
                total_claims=len(claim_objects),
                verified_claims_count=verified_count,
                unsupported_claims_count=unsupported_count,
                claims_detail=claim_objects,
            )

        # Áp dụng Selective Claim Pruning:
        # Nếu có claim bị unsupported nhưng còn các claim verified vững chắc
        if unsupported_count > 0 and valid_sentences:
            logger.info("Tier 4 QA Guard: Selective pruning applied (%d claims pruned)", unsupported_count)
            pruned_text = " ".join(valid_sentences)
            return QAAlignmentResult(
                is_aligned=True,
                trigger_refusal=False,
                pruned_answer=pruned_text,
                total_claims=len(claim_objects),
                verified_claims_count=verified_count,
                unsupported_claims_count=unsupported_count,
                claims_detail=claim_objects,
            )

        return QAAlignmentResult(
            is_aligned=True,
            trigger_refusal=False,
            pruned_answer=draft_answer,
            total_claims=len(claim_objects),
            verified_claims_count=verified_count,
            unsupported_claims_count=unsupported_count,
            claims_detail=claim_objects,
        )
